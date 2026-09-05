from __future__ import annotations

import io
import json
import os
import re
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from shutil import copyfileobj
from typing import TYPE_CHECKING, Any
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

import humanize
import pandas as pd
import requests
from packaging.version import InvalidVersion, Version
from tqdm import tqdm

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable, Mapping


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
    gold: bool
    optimized: bool
    ordered: bool
    area: bool
    wires: bool
    crossings: bool
    acp: bool
    none: bool


@dataclass
class ParsedBenchmarkName:
    benchmark: str
    level: str
    library: str
    clocking_scheme: str
    physical_design_algorithm: str
    optimized: str
    ordered: str
    cost: str
    x: int | str
    y: int | str
    area: int | str
    size_uncompressed: int
    size_compressed: int
    filename: str


class Backend:
    def __init__(self) -> None:
        self.trindade = [
            {"name": "Multiplexer 2:1", "id": "1", "filename": "mux21"},
            {"name": "XOR", "id": "2", "filename": "xor2"},
            {"name": "XNOR", "id": "3", "filename": "xnor2"},
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
            {"name": "2bitAdderMaj", "id": "17", "filename": "2bitaddermaj"},
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
        self.layout_dimensions: list[dict[str, dict[str, int]]] | None = None

    def filter_database(self, benchmark_config: BenchmarkConfiguration) -> pd.DataFrame:
        """Filter the database according to a benchmark configuration."""
        colnames = list(ParsedBenchmarkName.__annotations__.keys())
        if self.database is None or self.database.empty:
            return pd.DataFrame(columns=colnames)

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

        matching_benchmarks = self.database[self.database["benchmark"].isin(selected_benchmarks)]
        selected_rows: list[pd.DataFrame] = []

        if benchmark_config.gate:
            gate_rows = matching_benchmarks.loc[matching_benchmarks["level"] == "gate"]

            libraries = [
                library
                for library, selected in (("one", benchmark_config.one), ("bestagon", benchmark_config.bestagon))
                if selected
            ]
            if libraries:
                gate_rows = gate_rows.loc[gate_rows["library"].isin(libraries)]

            if benchmark_config.best:
                gate_rows = gate_rows.loc[gate_rows["clocking_scheme"] == "best"]
            else:
                clocking_schemes = [
                    scheme
                    for scheme, selected in (
                        ("2ddwave", benchmark_config.twoddwave),
                        ("use", benchmark_config.use),
                        ("res", benchmark_config.res),
                        ("esr", benchmark_config.esr),
                        ("row", benchmark_config.row),
                    )
                    if selected
                ]
                if clocking_schemes:
                    gate_rows = gate_rows.loc[gate_rows["clocking_scheme"].isin(clocking_schemes)]

                algorithms = [
                    algorithm
                    for algorithm, selected in (
                        ("exact", benchmark_config.exact),
                        ("nanoplacer", benchmark_config.nanoplacer),
                        ("ortho", benchmark_config.ortho),
                        ("gold", benchmark_config.gold),
                    )
                    if selected
                ]
                if algorithms:
                    algorithm_rows = []
                    costs = [
                        cost
                        for cost, selected in (
                            ("area", benchmark_config.area),
                            ("wires", benchmark_config.wires),
                            ("crossings", benchmark_config.crossings),
                            ("acp", benchmark_config.acp),
                            ("none", benchmark_config.none),
                        )
                        if selected
                    ]
                    for algorithm in algorithms:
                        rows = gate_rows.loc[gate_rows["physical_design_algorithm"] == algorithm]
                        if benchmark_config.optimized and algorithm != "exact":
                            rows = rows.loc[rows["optimized"] == "opt"]
                        if benchmark_config.ordered and algorithm == "ortho":
                            rows = rows.loc[rows["ordered"] == "ord"]
                        if costs and algorithm == "gold":
                            rows = rows.loc[rows["cost"].isin(costs)]
                        algorithm_rows.append(rows)
                    gate_rows = pd.concat(algorithm_rows, ignore_index=True)

            selected_rows.append(gate_rows)

        if benchmark_config.network:
            selected_rows.append(matching_benchmarks.loc[matching_benchmarks["level"] == "network"])

        if not selected_rows:
            return pd.DataFrame(columns=colnames)
        return pd.concat(selected_rows, ignore_index=True).drop_duplicates()

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

        try:
            with ZipFile(fileobj, mode="w", compression=ZIP_DEFLATED, compresslevel=3) as zf:
                for individual_file in filenames:
                    individual_file_as_path = Path(individual_file)
                    assert self.mntbench_all_zip is not None
                    with (
                        self.mntbench_all_zip.open(individual_file) as source,
                        zf.open(individual_file_as_path.name, mode="w", force_zip64=True) as destination,
                    ):
                        copyfileobj(source, destination, length=1024 * 1024)
                    fileobj.hidden_seek(0)
                    yield fileobj.read()
                    fileobj.truncate_and_remember_offset(0)

            fileobj.hidden_seek(0)
            yield fileobj.read()
        finally:
            fileobj.close()

    def get_updated_table(self, prepared_data: BenchmarkConfiguration) -> pd.DataFrame:
        """
        Get an updated table based on the provided prepared data.

        Parameters:
        - prepared_data: Filter configuration prepared from the submitted form.

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
            "xor2": "XOR",
            "xnor2": "XNOR",
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

        cost_mapping = {
            "area": "Area",
            "wires": "#Wires",
            "crossings": "#Crossings",
            "acp": "Area-Crossing Product",
            "none": "✗",
        }
        table.replace({"cost": cost_mapping}, inplace=True)

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
            "cost": "Cost Objective",
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
    def prepare_form_input(form_data: Mapping[str, str]) -> BenchmarkConfiguration:
        """Formats the formData extracted from the user's inputs."""
        indices_benchmarks = []
        for key in form_data:
            if key.startswith("selectBench_"):
                found_benchmark_id = parse_benchmark_id_from_form_key(key)
                if found_benchmark_id:
                    indices_benchmarks.append(found_benchmark_id)

        return BenchmarkConfiguration(
            indices_benchmarks=indices_benchmarks,
            gate="gate" in form_data,
            network="network" in form_data,
            one="one" in form_data,
            bestagon="bestagon" in form_data,
            twoddwave="twoddwave" in form_data,
            use="use" in form_data,
            res="res" in form_data,
            esr="esr" in form_data,
            row="row" in form_data,
            best="best-layout" in form_data,
            exact="exact" in form_data,
            ortho="ortho" in form_data,
            nanoplacer="nanoplacer" in form_data,
            gold="gold" in form_data,
            optimized="post-layout" in form_data,
            ordered="input-ordering" in form_data,
            area="area" in form_data,
            wires="wires" in form_data,
            crossings="crossings" in form_data,
            acp="acp" in form_data,
            none="none" in form_data,
        )

    def read_mntbench_all_zip(
        self,
        target_location: str,
        skip_question: bool = False,
    ) -> bool:
        huge_zip_path = Path(target_location) / "MNTBench_all.zip"
        expected_sizes = (
            {
                filename: int(dimensions["size_uncompressed"])
                for entry in self.layout_dimensions
                for filename, dimensions in entry.items()
            }
            if self.layout_dimensions
            else None
        )

        print("Searching for local benchmarks...")
        local_benchmarks_available = False
        if huge_zip_path.is_file():
            try:
                with ZipFile(huge_zip_path) as archive:
                    archive_entries = archive.infolist()
                    archive_sizes = {info.filename: info.file_size for info in archive_entries}
                    local_benchmarks_available = bool(archive_sizes) and (
                        expected_sizes is None
                        or (len(archive_entries) == len(expected_sizes) and archive_sizes == expected_sizes)
                    )
            except BadZipFile:
                print("Local benchmark archive is invalid.")

        if local_benchmarks_available:
            print("... found.")
        else:
            print("No benchmarks found. Querying GitHub...")
            try:
                mntbench_module_version = metadata.version("mnt.bench")
            except metadata.PackageNotFoundError:
                print(
                    "'mnt.bench' is not installed. Run 'python -m pip install .' or 'python -m pip install mnt.bench'."
                )
                return False
            installed_version = Version(mntbench_module_version)
            matching_releases: list[tuple[Version, str, dict[str, Any]]] = []
            for release in handle_github_api_request("releases?per_page=100").json():
                try:
                    release_version = Version(release["tag_name"])
                except (InvalidVersion, KeyError):
                    continue
                if installed_version < release_version:
                    continue
                asset = next(
                    (candidate for candidate in release.get("assets", []) if candidate["name"] == "MNTBench_all.zip"),
                    None,
                )
                if asset is not None:
                    matching_releases.append((release_version, release["tag_name"], asset))

            if not matching_releases:
                print("No suitable benchmarks found.")
                return False

            _, release_tag, asset = max(matching_releases, key=lambda candidate: candidate[0])
            download_url = asset["browser_download_url"]
            response = ""
            if not skip_question:
                file_size = round(asset["size"] / 2**20, 2)
                print(f"Found 'MNTBench_all.zip' ({release_tag}, {file_size} MB, {download_url})")
                response = input("Would you like to download the file? (Y/n) ")
            if not (skip_question or response.lower() == "y" or not response):
                print("Benchmark download cancelled.")
                return False
            self.handle_downloading_benchmarks(target_location, download_url, expected_sizes)

        if self.mntbench_all_zip is not None:
            self.mntbench_all_zip.close()
        self.mntbench_all_zip = ZipFile(huge_zip_path, mode="r")
        return True

    @staticmethod
    def handle_downloading_benchmarks(
        target_location: str,
        download_url: str,
        expected_sizes: Mapping[str, int] | None = None,
    ) -> None:
        print("Start downloading benchmarks...")
        destination = Path(target_location) / "MNTBench_all.zip"
        temporary_destination = destination.with_suffix(".zip.part")
        destination.parent.mkdir(parents=True, exist_ok=True)

        try:
            with requests.get(download_url, stream=True, timeout=(10, 60)) as response:
                response.raise_for_status()
                content_length = response.headers.get("content-length")
                total_length = int(content_length) if content_length is not None else None
                with (
                    temporary_destination.open("wb") as output,
                    tqdm(
                        desc=str(destination),
                        total=total_length,
                        unit="iB",
                        unit_scale=True,
                        unit_divisor=1024,
                    ) as progress,
                ):
                    for data in response.iter_content(chunk_size=1024 * 1024):
                        progress.update(output.write(data))
            with ZipFile(temporary_destination) as archive:
                archive_entries = archive.infolist()
                archive_sizes = {info.filename: info.file_size for info in archive_entries}
                if not archive_sizes:
                    msg = "Downloaded benchmark archive is empty."
                    raise BadZipFile(msg)
                if expected_sizes is not None and (
                    len(archive_entries) != len(expected_sizes) or archive_sizes != expected_sizes
                ):
                    msg = "Downloaded benchmark archive does not match this MNT Bench release."
                    raise BadZipFile(msg)
            temporary_destination.replace(destination)
        finally:
            temporary_destination.unlink(missing_ok=True)
        print(f"Download completed to {destination}. Server is starting now.")

    @staticmethod
    def read_layout_dimensions_from_json(target_location: str) -> list[dict[str, dict[str, int]]]:
        """Read layout metadata from ``layout_dimensions.json`` when it exists."""
        file_name = Path(target_location) / "layout_dimensions.json"
        try:
            with file_name.open(encoding="utf-8") as file:
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
            specs = filename.split(".", maxsplit=1)[0].lower().split("_")

            benchmark = "_".join(specs[0 : -(2 if is_best_fgl else 6)])
            if benchmark == "xor":
                benchmark = "xor2"
            library, clocking_scheme, *additional_specs = specs[-2:] if is_best_fgl else specs[-6:]
            physical_design_algorithm, optimized, ordered, cost = additional_specs + [""] * (4 - len(additional_specs))

            level = "gate"
            area = int(layout_dimensions.get("x", 0)) * int(layout_dimensions.get("y", 0)) if layout_dimensions else ""

        elif filename.endswith(".v"):
            benchmark = filename.split(".", maxsplit=1)[0].lower()
            library = clocking_scheme = physical_design_algorithm = optimized = ordered = cost = ""
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
            cost=cost,
            x=layout_dimensions.get("x", ""),
            y=layout_dimensions.get("y", ""),
            area=area,
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

    def seekable(self) -> bool:
        return False

    def hidden_seek(self, offset: int, start_point: int = io.SEEK_SET) -> int:
        return self.fp.seek(offset, start_point)

    def truncate_and_remember_offset(self, size: int | None) -> int:
        self.deleted_offset += self.fp.tell()
        self.fp.seek(0)
        return self.fp.truncate(size)

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


def handle_github_api_request(repo_url: str) -> requests.Response:
    """Query the MNT Bench GitHub API, using a token when one is available."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if github_token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {github_token}"

    response = requests.get(
        f"https://api.github.com/repos/cda-tum/mnt-bench/{repo_url}",
        headers=headers,
        timeout=30,
    )
    success_code = 200
    if response.status_code == success_code:
        return response

    msg = (
        f"Request to GitHub API failed with status code {response.status_code}!\n"
        "The unauthenticated GitHub API limit may have been exceeded. Set GITHUB_TOKEN to a personal access token "
        "to increase the limit."
    )
    raise RuntimeError(msg)
