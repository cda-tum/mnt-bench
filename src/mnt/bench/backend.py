from __future__ import annotations

import io
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast
from zipfile import ZIP_DEFLATED, ZipFile

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


@dataclass
class ParsedBenchmarkName:
    benchmark: str
    level: str
    library: str
    clocking_scheme: str
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
            {"name": "b1_r2", "id": "9", "filename": "b1_r2"},
            {"name": "majority", "id": "10", "filename": "majority"},
            {"name": "newtag", "id": "11", "filename": "newtag"},
            {"name": "clpl", "id": "12", "filename": "clpl"},
            {"name": "1bitAdderAOIG", "id": "13", "filename": "1bitadderaoig"},
            {"name": "1bitAdderMaj", "id": "14", "filename": "1bitaddermaj"},
            {"name": "2bitAdderAOIG", "id": "15", "filename": "2bitaddermaj"},
            {"name": "XOR5Maj", "id": "16", "filename": "xor5maj"},
            {"name": "cm82a_5", "id": "17", "filename": "cm82a_5"},
            {"name": "parity", "id": "18", "filename": "parity"},
        ]

        self.iscas = [
            {"name": "c17", "id": "19", "filename": "c17"},
            {"name": "c432", "id": "20", "filename": "c432"},
            {"name": "c499", "id": "21", "filename": "c499"},
            {"name": "c880", "id": "22", "filename": "c880"},
            {"name": "c1355", "id": "23", "filename": "c1355"},
            {"name": "c1908", "id": "24", "filename": "c1908"},
            {"name": "c2670", "id": "25", "filename": "c2670"},
            {"name": "c3540", "id": "26", "filename": "c3540"},
            {"name": "c5315", "id": "27", "filename": "c5315"},
            {"name": "c6288", "id": "28", "filename": "c6288"},
            {"name": "c7552", "id": "29", "filename": "c7552"},
        ]

        self.epfl = [
            {"name": "ctrl", "id": "30", "filename": "ctrl"},
            {"name": "router", "id": "31", "filename": "router"},
            {"name": "int2float", "id": "32", "filename": "int2float"},
            {"name": "cavlc", "id": "33", "filename": "cavlc"},
            {"name": "priority", "id": "34", "filename": "priority"},
            {"name": "dec", "id": "35", "filename": "dec"},
            {"name": "i2c", "id": "36", "filename": "i2c"},
            {"name": "adder", "id": "37", "filename": "adder"},
            {"name": "arbiter", "id": "38", "filename": "arbiter"},
            {"name": "bar", "id": "39", "filename": "bar"},
            {"name": "max", "id": "40", "filename": "max"},
            {"name": "sin", "id": "41", "filename": "sin"},
            {"name": "voter", "id": "42", "filename": "voter"},
            {"name": "square", "id": "43", "filename": "square"},
        ]

        self.database: pd.DataFrame | None = None
        self.mntbench_all_zip: ZipFile | None = None

    def filter_database(self, benchmark_config: BenchmarkConfiguration) -> list[str]:  # noqa: PLR0912, PLR0915
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

        if not (benchmark_config.one | benchmark_config.bestagon):
            if benchmark_config.network and not benchmark_config.gate:
                db_tmp = db_tmp.loc[db_tmp["level"] == "network"]
                db_filtered = pd.concat([db_filtered, db_tmp])

            if benchmark_config.gate and not benchmark_config.network:
                db_tmp = db_tmp.loc[db_tmp["level"] == "gate"]
                db_filtered = pd.concat([db_filtered, db_tmp])

            if benchmark_config.network and benchmark_config.gate:
                db_tmp = db_tmp.loc[(db_tmp["level"] == "network") | (db_tmp["level"] == "gate")]
                db_filtered = pd.concat([db_filtered, db_tmp])

        if benchmark_config.gate and not benchmark_config.network:
            if not (
                benchmark_config.twoddwave
                | benchmark_config.use
                | benchmark_config.res
                | benchmark_config.esr
                | benchmark_config.row
            ):
                if benchmark_config.one and not benchmark_config.bestagon:
                    db_tmp = db_tmp.loc[db_tmp["library"] == "one"]
                    db_filtered = pd.concat([db_filtered, db_tmp])

                if benchmark_config.bestagon and not benchmark_config.one:
                    db_tmp = db_tmp.loc[db_tmp["library"] == "bestagon"]
                    db_filtered = pd.concat([db_filtered, db_tmp])

                if benchmark_config.one and benchmark_config.bestagon:
                    db_tmp = db_tmp.loc[(db_tmp["library"] == "one") | (db_tmp["library"] == "bestagon")]
                    db_filtered = pd.concat([db_filtered, db_tmp])

            if benchmark_config.one and not benchmark_config.bestagon:
                db_tmp = db_tmp.loc[
                    (
                        (db_tmp["clocking_scheme"] == ("2ddwave" if benchmark_config.twoddwave else "-"))
                        | (db_tmp["clocking_scheme"] == ("use" if benchmark_config.use else "-"))
                        | (db_tmp["clocking_scheme"] == ("res" if benchmark_config.res else "-"))
                        | (db_tmp["clocking_scheme"] == ("esr" if benchmark_config.esr else "-"))
                    )
                    & (db_tmp["library"] == "one")
                ]
                db_filtered = pd.concat([db_filtered, db_tmp])

            if benchmark_config.bestagon and not benchmark_config.one:
                db_tmp = db_tmp.loc[(db_tmp["clocking_scheme"] == "row") & (db_tmp["library"] == "bestagon")]
                db_filtered = pd.concat([db_filtered, db_tmp])

            if benchmark_config.one and benchmark_config.bestagon:
                db_tmp = db_tmp.loc[
                    (
                        (
                            (db_tmp["clocking_scheme"] == ("2ddwave" if benchmark_config.twoddwave else "-"))
                            | (db_tmp["clocking_scheme"] == ("use" if benchmark_config.use else "-"))
                            | (db_tmp["clocking_scheme"] == ("res" if benchmark_config.res else "-"))
                            | (db_tmp["clocking_scheme"] == ("esr" if benchmark_config.esr else "-"))
                        )
                        & (db_tmp["library"] == "one")
                    )
                    | (
                        (db_tmp["clocking_scheme"] == ("row" if benchmark_config.row else "-"))
                        & (db_tmp["library"] == "bestagon")
                    )
                ]
                db_filtered = pd.concat([db_filtered, db_tmp])

        if benchmark_config.gate and benchmark_config.network:
            if not (
                benchmark_config.twoddwave
                | benchmark_config.use
                | benchmark_config.res
                | benchmark_config.esr
                | benchmark_config.row
            ):
                if benchmark_config.one and not benchmark_config.bestagon:
                    db_tmp = db_tmp.loc[(db_tmp["library"] == "one") | (db_tmp["level"] == "network")]
                    db_filtered = pd.concat([db_filtered, db_tmp])

                if benchmark_config.bestagon and not benchmark_config.one:
                    db_tmp = db_tmp.loc[(db_tmp["library"] == "bestagon") | (db_tmp["level"] == "network")]
                    db_filtered = pd.concat([db_filtered, db_tmp])

                if benchmark_config.one and benchmark_config.bestagon:
                    db_tmp = db_tmp.loc[
                        ((db_tmp["library"] == "one") | (db_tmp["library"] == "bestagon"))
                        | (db_tmp["level"] == "network")
                    ]
                    db_filtered = pd.concat([db_filtered, db_tmp])

            if benchmark_config.one and not benchmark_config.bestagon:
                db_tmp = db_tmp.loc[
                    (
                        (
                            (db_tmp["clocking_scheme"] == ("2ddwave" if benchmark_config.twoddwave else "-"))
                            | (db_tmp["clocking_scheme"] == ("use" if benchmark_config.use else "-"))
                            | (db_tmp["clocking_scheme"] == ("res" if benchmark_config.res else "-"))
                            | (db_tmp["clocking_scheme"] == ("esr" if benchmark_config.esr else "-"))
                        )
                        & (db_tmp["library"] == "one")
                    )
                    | (db_tmp["level"] == "network")
                ]
                db_filtered = pd.concat([db_filtered, db_tmp])

            if benchmark_config.bestagon and not benchmark_config.one:
                db_tmp = db_tmp.loc[
                    ((db_tmp["clocking_scheme"] == "row") & (db_tmp["library"] == "bestagon"))
                    | (db_tmp["level"] == "network")
                ]
                db_filtered = pd.concat([db_filtered, db_tmp])

            if benchmark_config.one and benchmark_config.bestagon:
                db_tmp = db_tmp.loc[
                    (
                        (
                            (
                                (db_tmp["clocking_scheme"] == ("2ddwave" if benchmark_config.twoddwave else "-"))
                                | (db_tmp["clocking_scheme"] == ("use" if benchmark_config.use else "-"))
                                | (db_tmp["clocking_scheme"] == ("res" if benchmark_config.res else "-"))
                                | (db_tmp["clocking_scheme"] == ("esr" if benchmark_config.esr else "-"))
                            )
                            & (db_tmp["library"] == "one")
                        )
                        | (
                            (db_tmp["clocking_scheme"] == ("row" if benchmark_config.row else "-"))
                            & (db_tmp["library"] == "bestagon")
                        )
                    )
                    | (db_tmp["level"] == "network")
                ]
                db_filtered = pd.concat([db_filtered, db_tmp])
        db_filtered = db_filtered.drop_duplicates()
        return cast(list[str], db_filtered["filename"].to_list())

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

    def get_selected_file_paths(self, prepared_data: BenchmarkConfiguration) -> list[str]:
        """Extracts all file paths according to the prepared user's filter criteria.

        Keyword arguments:
        prepared_data -- user's filter criteria after preparation step

        Return values:
        file_paths -- list of filter criteria for each selected benchmark
        """
        return self.filter_database(prepared_data)

    def init_database(self) -> bool:
        """Generates the database and saves it into a global variable."""

        assert self.mntbench_all_zip is not None

        print("Initiating database...")
        self.database = create_database(self.mntbench_all_zip)
        print(f"... done: {len(self.database)} benchmarks.")

        if not self.database.empty:
            return True

        print("Database initialization failed.")
        return False

    def prepare_form_input(self, form_data: dict[str, str]) -> BenchmarkConfiguration:
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
        )

    def read_mntbench_all_zip(  # noqa: PLR0912
        self,
        target_location: str,
        skip_question: bool = False,
    ) -> bool:
        huge_zip_path = Path(target_location) / "MNTBench_all.zip"

        try:
            mntbench_module_version = metadata.version("mnt.bench")
        except Exception:
            print("'mnt.bench' is most likely not installed. Please run 'pip install . or pip install mnt.bench'.")
            return False

        print("Searching for local benchmarks...")
        if huge_zip_path.is_file() and len(ZipFile(huge_zip_path, "r").namelist()) != 0:
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

    def handle_downloading_benchmarks(self, target_location: str, download_url: str) -> None:
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


def parse_data(filename: str) -> ParsedBenchmarkName:
    """Extracts the necessary information from a given filename.

    Keyword arguments:
    filename -- name of file

    Return values:
    parsed_data -- parsed data extracted from filename
    """
    if filename.endswith(".fgl"):
        benchmark = "_".join([file.lower() for file in filename.split("_")[0:-2]])
        library = filename.split("_")[-2].lower()
        clocking_scheme = filename.split("_")[-1].lower().split(".")[0]
        level = "gate"
    elif filename.endswith(".v"):
        benchmark = filename.split(".")[0].lower()
        library = ""
        clocking_scheme = ""
        level = "network"
    else:
        msg = "Unknown file type in MNTBench_all.zip"
        raise RuntimeError(msg)

    return ParsedBenchmarkName(
        benchmark=benchmark,
        level=level,
        library=library,
        clocking_scheme=clocking_scheme,
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


def create_database(zip_file: ZipFile) -> pd.DataFrame:
    """Creates the database based on the provided directories.
    Keyword arguments:
    qasm_path -- zip containing all .qasm files
    Return values:
    database -- database containing all available benchmarks
    """
    rows_list = []

    for filename in zip_file.namelist():
        if filename.endswith((".fgl", ".v")):
            parsed_data = parse_data(filename)
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
