from __future__ import annotations

import io
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from zipfile import ZIP_DEFLATED, ZipFile

import humanize  # type: ignore[import-not-found]
import pandas as pd
import requests
from packaging import version
from tqdm import tqdm

if TYPE_CHECKING or sys.version_info >= (3, 10, 0):  # pragma: no cover
    from importlib import metadata
else:
    import importlib_metadata as metadata


if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable


@dataclass
class BenchmarkConfiguration:
    indices_benchmarks: list[int]
    network: bool
    gate: bool
    one: bool
    bestagon: bool
    twoddwave: bool
    use: bool
    res: bool
    esr: bool
    row: bool
    best: bool
    exact: bool
    ortho: bool
    nanoplacer: bool
    optimized: bool
    ordered: bool


@dataclass
class ParsedBenchmarkName:
    benchmark: str
    level: str
    library: str
    clocking_scheme: str
    physical_design_algorithm: str
    optimized: str
    ordered: str
    x: int
    y: int
    area: int
    size_uncompressed: int
    size_compressed: int
    filename: str


class Backend:
    def __init__(self) -> None:
        self.trindade = [
            {"name": "Multiplexer 2:1", "id": "1", "filename": "mux21"},
            {"name": "XOR 2:1", "id": "2", "filename": "xor2"},
            {"name": "XNOR 2:1", "id": "3", "filename": "xnor2"},
            {"name": "Half Adder", "id": "4", "filename": "ha"},
            {"name": "Full Adder", "id": "5", "filename": "fa"},
            {"name": "Parity Generator", "id": "6", "filename": "par_gen"},
            {"name": "Parity Check", "id": "7", "filename": "par_check"},
        ]

        self.fontes = [
            {"name": "t", "id": "8", "filename": "t"},
            {"name": "t_5", "id": "9", "filename": "t_5"},
            {"name": "b1_r2", "id": "10", "filename": "b1_r2"},
            {"name": "majority", "id": "11", "filename": "majority"},
            {"name": "majority_5_r1", "id": "12", "filename": "majority_5_r1"},
            {"name": "newtag", "id": "13", "filename": "newtag"},
            {"name": "clpl", "id": "14", "filename": "clpl"},
            {"name": "1bitAdderAOIG", "id": "15", "filename": "1bitadderaoig"},
            {"name": "1bitAdderMaj", "id": "16", "filename": "1bitaddermaj"},
            {"name": "2bitAdderAOIG", "id": "17", "filename": "2bitaddermaj"},
            {"name": "XOR5Maj", "id": "18", "filename": "xor5maj"},
            {"name": "xor5_r1", "id": "19", "filename": "xor5_r1"},
            {"name": "cm82a_5", "id": "20", "filename": "cm82a_5"},
            {"name": "parity", "id": "21", "filename": "parity"},
        ]

        self.iscas = [
            {"name": "c17", "id": "22", "filename": "c17"},
            {"name": "c432", "id": "23", "filename": "c432"},
            {"name": "c499", "id": "24", "filename": "c499"},
            {"name": "c880", "id": "25", "filename": "c880"},
            {"name": "c1355", "id": "26", "filename": "c1355"},
            {"name": "c1908", "id": "27", "filename": "c1908"},
            {"name": "c2670", "id": "28", "filename": "c2670"},
            {"name": "c3540", "id": "29", "filename": "c3540"},
            {"name": "c5315", "id": "30", "filename": "c5315"},
            {"name": "c6288", "id": "31", "filename": "c6288"},
            {"name": "c7552", "id": "32", "filename": "c7552"},
        ]

        self.epfl = [
            {"name": "ctrl", "id": "33", "filename": "ctrl"},
            {"name": "router", "id": "34", "filename": "router"},
            {"name": "int2float", "id": "35", "filename": "int2float"},
            {"name": "cavlc", "id": "36", "filename": "cavlc"},
            {"name": "priority", "id": "37", "filename": "priority"},
            {"name": "dec", "id": "38", "filename": "dec"},
            {"name": "i2c", "id": "39", "filename": "i2c"},
            {"name": "adder", "id": "40", "filename": "adder"},
            {"name": "bar", "id": "41", "filename": "bar"},
            {"name": "max", "id": "42", "filename": "max"},
            {"name": "sin", "id": "43", "filename": "sin"},
        ]

        self.database: pd.DataFrame | None = None
        self.mntbench_all_zip: ZipFile | None = None
        self.layout_dimensions: list[dict[str, dict[str, str]]] | None = None

    def filter_database(self, benchmark_config: BenchmarkConfiguration) -> pd.DataFrame:  # noqa: PLR0912, PLR0915
        """Filters the database according to the filter criteria.

        Keyword arguments:
        filterCriteria -- list of all filter criteria
        database -- database containing all available benchmarks


        Return values:
        db_filtered["path"].to_list() -- list of all file paths of the selected benchmark files
        """
        colnames = list(ParsedBenchmarkName.__annotations__.keys())
        db_filtered = pd.DataFrame(columns=colnames)

        if self.database is None or self.database.empty:
            return []

        selected_benchmarks = []
        for identifier in benchmark_config.indices_benchmarks:
            if 1 <= identifier <= len(self.trindade):
                selected_benchmarks.append(self.trindade[identifier - 1]["filename"])
            elif 1 <= identifier <= len(self.trindade) + len(self.fontes):
                selected_benchmarks.append(self.fontes[identifier - 1 - len(self.trindade)]["filename"])
            elif 1 <= identifier <= len(self.trindade) + len(self.fontes) + len(self.iscas):
                selected_benchmarks.append(
                    self.iscas[identifier - 1 - len(self.trindade) - len(self.fontes)]["filename"]
                )
            elif 1 <= identifier <= len(self.trindade) + len(self.fontes) + len(self.iscas) + len(self.epfl):
                selected_benchmarks.append(
                    self.epfl[identifier - 1 - len(self.trindade) - len(self.fontes) - len(self.iscas)]["filename"]
                )

        db_tmp = self.database[self.database["benchmark"].isin(selected_benchmarks)]
        db_networks = db_tmp.loc[db_tmp["level"] == "network"]

        if benchmark_config.gate:
            db_tmp = db_tmp.loc[db_tmp["level"] == "gate"]
            db_filtered = pd.concat([db_filtered if not db_filtered.empty else None, db_tmp])

            if benchmark_config.one and not benchmark_config.bestagon:
                db_filtered = db_tmp.loc[db_tmp["library"] == "one"]

            if not benchmark_config.one and benchmark_config.bestagon:
                db_filtered = db_tmp.loc[db_tmp["library"] == "bestagon"]

            if benchmark_config.best:
                db_filtered = db_filtered.loc[db_filtered["clocking_scheme"] == "best"]
            else:
                db_tmp_all_schemes = pd.DataFrame(columns=colnames)
                if benchmark_config.twoddwave:
                    db_tmp = db_filtered.loc[db_filtered["clocking_scheme"] == "2ddwave"]
                    db_tmp_all_schemes = pd.concat(
                        [db_tmp_all_schemes if not db_tmp_all_schemes.empty else None, db_tmp]
                    )

                if benchmark_config.use:
                    db_tmp = db_filtered.loc[db_filtered["clocking_scheme"] == "use"]
                    db_tmp_all_schemes = pd.concat(
                        [db_tmp_all_schemes if not db_tmp_all_schemes.empty else None, db_tmp]
                    )

                if benchmark_config.res:
                    db_tmp = db_filtered.loc[db_filtered["clocking_scheme"] == "res"]
                    db_tmp_all_schemes = pd.concat(
                        [db_tmp_all_schemes if not db_tmp_all_schemes.empty else None, db_tmp]
                    )

                if benchmark_config.esr:
                    db_tmp = db_filtered.loc[db_filtered["clocking_scheme"] == "esr"]
                    db_tmp_all_schemes = pd.concat(
                        [db_tmp_all_schemes if not db_tmp_all_schemes.empty else None, db_tmp]
                    )

                if benchmark_config.row:
                    db_tmp = db_filtered.loc[db_filtered["clocking_scheme"] == "row"]
                    db_tmp_all_schemes = pd.concat(
                        [db_tmp_all_schemes if not db_tmp_all_schemes.empty else None, db_tmp]
                    )

                if not db_tmp_all_schemes.empty:
                    db_filtered = db_tmp_all_schemes

                if benchmark_config.exact:
                    db_filtered = db_filtered.loc[db_filtered["physical_design_algorithm"] == "exact"]

                if benchmark_config.nanoplacer:
                    db_filtered = db_filtered.loc[db_filtered["physical_design_algorithm"] == "nanoplacer"]

                    if benchmark_config.optimized:
                        db_filtered = db_filtered.loc[db_filtered["optimized"] == "opt"]

                if benchmark_config.ortho:
                    db_filtered = db_filtered.loc[db_filtered["physical_design_algorithm"] == "ortho"]

                    if benchmark_config.optimized:
                        db_filtered = db_filtered.loc[db_filtered["optimized"] == "opt"]

                    if benchmark_config.ordered:
                        db_filtered = db_filtered.loc[db_filtered["ordered"] == "ord"]

        if benchmark_config.network:
            db_filtered = pd.concat([db_filtered if not db_filtered.empty else None, db_networks])

        return db_filtered.drop_duplicates()

    def generate_zip_ephemeral_chunks(
        self,
        filenames: list[str],
    ) -> Iterable[bytes]:
        """Generates the zip file for the selected benchmarks and returns a generator of the chunks.

        Keyword arguments:
        paths -- list of file paths for all selected benchmarks

        Return values:
            Generator of bytes to send to the browser
        """
        fileobj = NoSeekBytesIO(io.BytesIO())

        with ZipFile(fileobj, mode="w") as zf:  # type: ignore[arg-type]
            for individual_file in filenames:
                individual_file_as_path = Path(individual_file)
                assert self.mntbench_all_zip is not None
                zf.writestr(
                    individual_file_as_path.name,
                    data=self.mntbench_all_zip.read(individual_file),
                    compress_type=ZIP_DEFLATED,
                    compresslevel=3,
                )
                fileobj.hidden_seek(0)
                yield fileobj.read()
                fileobj.truncate_and_remember_offset(0)

        fileobj.hidden_seek(0)
        yield fileobj.read()
        fileobj.close()

    def get_updated_table(self, prepared_data: pd.DataFrame) -> pd.DataFrame:
        """
        Get an updated table based on the provided prepared data.

        Parameters:
        - prepared_data (pd.DataFrame): A DataFrame containing prepared data for filtering.

        Returns:
        - pd.DataFrame: The updated table after applying filters using the filter_database method.
        """
        return self.filter_database(prepared_data)

    @staticmethod
    def prettify_table(table: pd.DataFrame) -> pd.DataFrame:
        """
        Prettify the given DataFrame by replacing certain values and renaming columns.

        Parameters:
        - table (pd.DataFrame): The DataFrame to be prettified.

        Returns:
        - pd.DataFrame: The prettified DataFrame.
        """
        benchmark_mapping = {
            "mux21": "MUX 2:1",
            "xor2": "XOR 2:1",
            "xnor2": "XNOR 2:1",
            "ha": "Half Adder",
            "fa": "Full Adder",
            "par_gen": "Parity Generator",
            "par_check": "Parity Check",
        }
        table.replace({"benchmark": benchmark_mapping}, inplace=True)

        level_mapping = {"gate": "Gate-level", "network": "Network"}
        table.replace({"level": level_mapping}, inplace=True)

        library_mapping = {"one": "QCA ONE", "bestagon": "Bestagon"}
        table.replace({"library": library_mapping}, inplace=True)

        clocking_scheme_mapping = {"2ddwave": "2DDWave", "use": "USE", "res": "RES", "esr": "ESR", "row": "ROW"}
        table.replace({"clocking_scheme": clocking_scheme_mapping}, inplace=True)

        physical_design_algorithm_mapping = {"nanoplacer": "NanoPlaceR"}
        table.replace({"physical_design_algorithm": physical_design_algorithm_mapping}, inplace=True)

        opt_mapping = {"opt": "✓", "unopt": "✗"}
        table.replace({"optimized": opt_mapping}, inplace=True)

        ord_mapping = {"ord": "✓", "unord": "✗"}
        table.replace({"ordered": ord_mapping}, inplace=True)

        table["size_compressed"] = table["size_compressed"].apply(humanize.naturalsize)
        table["size_uncompressed"] = table["size_uncompressed"].apply(humanize.naturalsize)

        column_mapping = {
            "benchmark": "Benchmark Function",
            "level": "Abstraction Level",
            "library": "Gate Library",
            "clocking_scheme": "Clocking Scheme",
            "physical_design_algorithm": "Physical Design Algorithm",
            "optimized": "Post-Layout Optimization",
            "ordered": "Input-Ordering",
            "x": "Layout Width",
            "y": "Layout Height",
            "area": "Layout Area",
            "size_uncompressed": "File Size (uncompressed)",
            "size_compressed": "File Size (compressed)",
            "filename": "Filename",
        }
        table.columns = [column_mapping.get(col, col) for col in table.columns]
        return table

    @staticmethod
    def get_selected_file_paths(table: pd.DataFrame) -> list[str]:
        """
        Get a list of selected file paths from the given DataFrame.

        Parameters:
        - table (pd.DataFrame): The DataFrame containing a column named 'filename'.

        Returns:
        - List[str]: A list of file paths extracted from the 'filename' column.
        """
        return [str(item) for item in table["filename"].to_list()]

    def init_database(self) -> bool:
        """Generates the database and saves it into a global variable."""

        assert self.mntbench_all_zip is not None

        print("Initiating database...")
        self.database = create_database(self, self.mntbench_all_zip)
        print(f"... done: {len(self.database)} benchmarks.")

        if not self.database.empty:
            return True

        print("Database initialization failed.")
        return False

    @staticmethod
    def prepare_form_input(form_data: dict[str, str]) -> BenchmarkConfiguration:
        """Formats the formData extracted from the user's inputs."""
        indices_benchmarks = []
        network = False
        gate = False
        one = False
        bestagon = False
        twoddwave = False
        use = False
        res = False
        esr = False
        row = False
        best = False
        exact = False
        ortho = False
        nanoplacer = False
        optimized = False
        ordered = False

        for k in form_data:
            if "select" in k:
                found_benchmark_id = parse_benchmark_id_from_form_key(k)
                if found_benchmark_id:
                    indices_benchmarks.append(found_benchmark_id)

            network = "network" in k or network
            gate = "gate" in k or gate
            one = "one" in k or one
            bestagon = "bestagon" in k or bestagon
            twoddwave = "twoddwave" in k or twoddwave
            use = "use" in k or use
            res = "res" in k or res
            esr = "esr" in k or esr
            row = "row" in k or row
            best = "best-layout" in k or best
            exact = "exact" in k or exact
            ortho = "ortho" in k or ortho
            nanoplacer = "nanoplacer" in k or nanoplacer
            optimized = "post-layout" in k or optimized
            ordered = "input-ordering" in k or ordered

        return BenchmarkConfiguration(
            indices_benchmarks=indices_benchmarks,
            gate=gate,
            network=network,
            one=one,
            bestagon=bestagon,
            twoddwave=twoddwave,
            use=use,
            res=res,
            esr=esr,
            row=row,
            best=best,
            exact=exact,
            ortho=ortho,
            nanoplacer=nanoplacer,
            optimized=optimized,
            ordered=ordered,
        )

    def read_mntbench_all_zip(  # noqa: PLR0912
        self,
        target_location: str,
        skip_question: bool = False,
        test: bool = False,
    ) -> bool:
        huge_zip_path = Path(target_location) / "MNTBench_all.zip"

        try:
            mntbench_module_version = metadata.version("mnt.bench")
        except Exception:
            print("'mnt.bench' is most likely not installed. Please run 'pip install . or pip install mnt.bench'.")
            return False

        print("Searching for local benchmarks...")
        if (not skip_question or test) and huge_zip_path.is_file() and len(ZipFile(huge_zip_path, "r").namelist()) != 0:
            print("... found.")
        else:
            print("No benchmarks found. Querying GitHub...")

            version_found = False
            available_versions = []
            for elem in handle_github_api_request("tags").json():
                available_versions.append(elem["name"])

            for possible_version in available_versions:
                if version.parse(mntbench_module_version) >= version.parse(possible_version):
                    response_json = handle_github_api_request(f"releases/tags/{possible_version}").json()
                    if "assets" in response_json:
                        assets = response_json["assets"]
                    elif "asset" in response_json:
                        assets = [response_json["asset"]]
                    else:
                        assets = []

                    for asset in assets:
                        if asset["name"] == "MNTBench_all.zip":
                            version_found = True

                        if version_found:
                            download_url = asset["browser_download_url"]
                            response = "n"
                            if not skip_question:
                                file_size = round((asset["size"]) / 2**20, 2)
                                print(
                                    "Found 'MNTBench_all.zip' (Version {}, Size {} MB, Link: {})".format(
                                        possible_version,
                                        file_size,
                                        download_url,
                                    )
                                )
                                response = input("Would you like to downloaded the file? (Y/n)")
                            if skip_question or response.lower() == "y" or not response:
                                self.handle_downloading_benchmarks(target_location, download_url)
                                break
                if version_found:
                    break

            if not version_found:
                print("No suitable benchmarks found.")
                return False

        with huge_zip_path.open("rb") as zf:
            zip_bytes = io.BytesIO(zf.read())
            self.mntbench_all_zip = ZipFile(zip_bytes, mode="r")
        return True

    @staticmethod
    def handle_downloading_benchmarks(target_location: str, download_url: str) -> None:
        print("Start downloading benchmarks...")

        r = requests.get(download_url, stream=True)

        content_length_response = r.headers.get("content-length")
        assert content_length_response is not None
        total_length = int(content_length_response)
        fname = target_location + "/MNTBench_all.zip"

        Path(target_location).mkdir(parents=True, exist_ok=True)
        with Path(fname).open("wb") as f, tqdm(
            desc=fname,
            total=total_length,
            unit="iB",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in r.iter_content(chunk_size=1024):
                size = f.write(data)
                bar.update(size)
        print(f"Download completed to {fname}. Server is starting now.")

    @staticmethod
    def read_layout_dimensions_from_json(target_location: str) -> list[dict[str, dict[str, str]]] | None:
        """
        Read layout dimensions from a JSON file.

        Parameters:
            target_location (str): The directory where the 'layout_dimensions.json' file is located.

        Returns:
            Union[List[Dict[str, Any]], None]: A list of dictionaries representing layout dimensions,
            or None if the file is not found.

        Raises:
            FileNotFoundError: If the 'layout_dimensions.json' file is not found.
        """
        file_name = target_location + "/layout_dimensions.json"
        try:
            with open(file_name) as file:  # noqa: PTH123
                return json.load(file)  # type: ignore[no-any-return]
        except FileNotFoundError:
            return []

    def parse_data(self, filename: str) -> ParsedBenchmarkName:
        """Extracts the necessary information from a given filename.

        Args:
        backend: The backend object containing layout dimensions.
        filename (str): The name of the file.

        Returns:
        ParsedBenchmarkName: Parsed data extracted from the filename.
        """
        layout_dimensions: Any = next((entry for entry in self.layout_dimensions if filename in entry), {})  # type: ignore[union-attr]
        layout_dimensions = layout_dimensions.get(filename, {})

        if filename.endswith(".fgl"):
            is_best_fgl = "best.fgl" in filename.lower()
            specs = filename.split(".")[0].lower().split("_")

            benchmark = "_".join(specs[0 : -(2 if is_best_fgl else 5)])
            library, clocking_scheme, *additional_specs = specs[-2:] if is_best_fgl else specs[-5:]
            physical_design_algorithm, optimized, ordered = additional_specs + [""] * (3 - len(additional_specs))

            level = "gate"
            area = int(layout_dimensions.get("x", 0)) * int(layout_dimensions.get("y", 0)) if layout_dimensions else ""

        elif filename.endswith(".v"):
            benchmark = filename.split(".")[0].lower()
            library = clocking_scheme = physical_design_algorithm = optimized = ordered = ""
            level = "network"
            area = ""

        else:
            msg = "Unknown file type in MNTBench_all.zip"
            raise RuntimeError(msg)

        size_uncompressed = round(layout_dimensions.get("size_uncompressed", 0))
        size_compressed = round(layout_dimensions.get("size_compressed", 0))

        return ParsedBenchmarkName(
            benchmark=benchmark,
            level=level,
            library=library,
            clocking_scheme=clocking_scheme,
            physical_design_algorithm=physical_design_algorithm,
            optimized=optimized,
            ordered=ordered,
            x=layout_dimensions.get("x", ""),
            y=layout_dimensions.get("y", ""),
            area=area,  # type: ignore[arg-type]
            size_uncompressed=size_uncompressed,
            size_compressed=size_compressed,
            filename=filename,
        )


class NoSeekBytesIO:
    def __init__(self, fp: io.BytesIO) -> None:
        self.fp = fp
        self.deleted_offset = 0

    def write(self, b: bytes) -> int:
        return self.fp.write(b)

    def tell(self) -> int:
        return self.deleted_offset + self.fp.tell()

    def hidden_tell(self) -> int:
        return self.fp.tell()

    def seekable(self) -> bool:
        return False

    def hidden_seek(self, offset: int, start_point: int = io.SEEK_SET) -> int:
        return self.fp.seek(offset, start_point)

    def truncate_and_remember_offset(self, size: int | None) -> int:
        self.deleted_offset += self.fp.tell()
        self.fp.seek(0)
        return self.fp.truncate(size)

    def get_value(self) -> bytes:
        return self.fp.getvalue()

    def close(self) -> None:
        return self.fp.close()

    def read(self) -> bytes:
        return self.fp.read()

    def flush(self) -> None:
        return self.fp.flush()


def parse_benchmark_id_from_form_key(k: str) -> int | bool:
    pat = re.compile(r"_\d+")
    m = pat.search(k)
    if m:
        return int(m.group()[1:])
    return False


def create_database(backend: Backend, zip_file: ZipFile) -> pd.DataFrame:
    """Creates the database based on the provided directories.
    Keyword arguments:
    backend -- website backend
    zip_file -- zip containing all .fgl and .v files
    Return values:
    database -- database containing all available benchmarks
    """
    rows_list = []

    for filename in zip_file.namelist():
        if filename.endswith((".fgl", ".v")):
            parsed_data = backend.parse_data(filename)
            rows_list.append(parsed_data)

    colnames = list(ParsedBenchmarkName.__annotations__.keys())

    return pd.DataFrame(rows_list, columns=colnames)


def handle_downloading_benchmarks(target_location: str, download_url: str) -> None:
    print("Start downloading benchmarks...")

    r = requests.get(download_url)
    total_length = int(r.headers["content-length"])

    fname = target_location + "/MNTBench_all.zip"

    Path(target_location).mkdir(parents=True, exist_ok=True)
    with Path(fname).open("wb") as f, tqdm(
        desc=fname,
        total=total_length,
        unit="iB",
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in r.iter_content(chunk_size=1024):
            size = f.write(data)
            bar.update(size)
    print(f"Download completed to {fname}. Server is starting now.")


def handle_github_api_request(repo_url: str) -> requests.Response:
    # If the environment variable GITHUB_TOKEN is set, use it to authenticate to the GitHub API
    # to increase the rate limit from 60 to 5000 requests per hour per IP address.
    headers = None
    if "GITHUB_TOKEN" in os.environ:
        headers = {"Authorization": f"token {os.environ['GITHUB_TOKEN']}"}

    response = requests.get(f"https://api.github.com/repos/cda-tum/mnt-bench/{repo_url}", headers=headers)
    success_code = 200
    if response.status_code == success_code:
        return response

    msg = (
        f"Request to GitHub API failed with status code {response.status_code}!\n"
        f"One reasons could be that the limit of 60 API calls per hour and IP address is exceeded.\n"
        f"If you want to increase the limit, set the environment variable GITHUB_TOKEN to a GitHub personal access token.\n"
        f"See https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token for more information."
    )
    raise RuntimeError(msg)
