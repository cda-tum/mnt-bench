from __future__ import annotations

from dataclasses import replace
from importlib import metadata, resources
from io import BytesIO, StringIO
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

import pandas as pd
import pytest

import mnt.bench.main as main_module
from mnt.bench import Backend, BenchmarkConfiguration, Server
from mnt.bench import backend as backend_module
from mnt.bench.main import app, main

if TYPE_CHECKING:
    from collections.abc import Iterator

    from flask.testing import FlaskClient

PACKAGE_FILES = resources.files("mnt.bench") / "static" / "files"
TARGET_LOCATION = str(PACKAGE_FILES)
BENCHMARK_FILENAMES = (
    "mux21_ONE_BEST.fgl",
    "mux21_ONE_2DDWave_exact_UnOpt_UnOrd_area.fgl",
    "mux21_ONE_2DDWave_NanoPlaceR_UnOpt_UnOrd_area.fgl",
    "mux21_ONE_2DDWave_ortho_UnOpt_UnOrd_none.fgl",
    "mux21_ONE_2DDWave_ortho_Opt_Ord_none.fgl",
    "mux21_ONE_2DDWave_gold_UnOpt_UnOrd_area.fgl",
    "mux21_ONE_2DDWave_gold_UnOpt_UnOrd_wires.fgl",
    "mux21.v",
)
FIXTURE_LAYOUT_DIMENSIONS = [
    {
        filename: {
            "x": 1,
            "y": 1,
            "size_compressed": 1,
            "size_uncompressed": len(f"fixture:{filename}".encode()),
        }
    }
    for filename in BENCHMARK_FILENAMES
]

BASE_CONFIGURATION = BenchmarkConfiguration(
    indices_benchmarks=[1],
    network=False,
    gate=False,
    one=False,
    bestagon=False,
    twoddwave=False,
    use=False,
    res=False,
    esr=False,
    row=False,
    best=False,
    exact=False,
    ortho=False,
    nanoplacer=False,
    gold=False,
    optimized=False,
    ordered=False,
    area=False,
    wires=False,
    crossings=False,
    acp=False,
    none=False,
)


@pytest.fixture
def benchmark_directory(tmp_path: Path) -> Path:
    with ZipFile(tmp_path / "MNTBench_all.zip", mode="w") as archive:
        for filename in BENCHMARK_FILENAMES:
            archive.writestr(filename, f"fixture:{filename}")
    return tmp_path


@pytest.fixture
def initialized_backend(benchmark_directory: Path) -> Backend:
    bench_backend = Backend()
    bench_backend.layout_dimensions = FIXTURE_LAYOUT_DIMENSIONS
    assert bench_backend.read_mntbench_all_zip(str(benchmark_directory), skip_question=True)
    assert bench_backend.init_database()
    return bench_backend


@pytest.mark.parametrize(
    ("filename", "expected_res"),
    [
        (
            "mux21_ONE_2DDWave_exact_UnOpt_UnOrd_area.fgl",
            backend_module.ParsedBenchmarkName(
                benchmark="mux21",
                level="gate",
                library="one",
                clocking_scheme="2ddwave",
                physical_design_algorithm="exact",
                optimized="unopt",
                ordered="unord",
                cost="area",
                x=3,
                y=4,
                area=12,
                size_compressed=517,
                size_uncompressed=3513,
                filename="mux21_ONE_2DDWave_exact_UnOpt_UnOrd_area.fgl",
            ),
        ),
        (
            "mux21_ONE_2DDWave_ortho_Opt_Ord_none.fgl",
            backend_module.ParsedBenchmarkName(
                benchmark="mux21",
                level="gate",
                library="one",
                clocking_scheme="2ddwave",
                physical_design_algorithm="ortho",
                optimized="opt",
                ordered="ord",
                cost="none",
                x=4,
                y=3,
                area=12,
                size_compressed=518,
                size_uncompressed=3513,
                filename="mux21_ONE_2DDWave_ortho_Opt_Ord_none.fgl",
            ),
        ),
        (
            "parity_Bestagon_ROW_gold_UnOpt_UnOrd_wires.fgl",
            backend_module.ParsedBenchmarkName(
                benchmark="parity",
                level="gate",
                library="bestagon",
                clocking_scheme="row",
                physical_design_algorithm="gold",
                optimized="unopt",
                ordered="unord",
                cost="wires",
                x=9,
                y=21,
                area=189,
                size_compressed=1312,
                size_uncompressed=18296,
                filename="parity_Bestagon_ROW_gold_UnOpt_UnOrd_wires.fgl",
            ),
        ),
        (
            "t_ONE_USE_exact_UnOpt_UnOrd_area.fgl",
            backend_module.ParsedBenchmarkName(
                benchmark="t",
                level="gate",
                library="one",
                clocking_scheme="use",
                physical_design_algorithm="exact",
                optimized="unopt",
                ordered="unord",
                cost="area",
                x=6,
                y=6,
                area=36,
                size_compressed=843,
                size_uncompressed=10421,
                filename="t_ONE_USE_exact_UnOpt_UnOrd_area.fgl",
            ),
        ),
        (
            "xor_ONE_2DDWave_gold_UnOpt_UnOrd_area.fgl",
            backend_module.ParsedBenchmarkName(
                benchmark="xor2",
                level="gate",
                library="one",
                clocking_scheme="2ddwave",
                physical_design_algorithm="gold",
                optimized="unopt",
                ordered="unord",
                cost="area",
                x=5,
                y=3,
                area=15,
                size_compressed=551,
                size_uncompressed=4494,
                filename="xor_ONE_2DDWave_gold_UnOpt_UnOrd_area.fgl",
            ),
        ),
        (
            "clpl.v",
            backend_module.ParsedBenchmarkName(
                benchmark="clpl",
                level="network",
                library="",
                clocking_scheme="",
                physical_design_algorithm="",
                optimized="",
                ordered="",
                cost="",
                x="",
                y="",
                area="",
                size_compressed=277,
                size_uncompressed=682,
                filename="clpl.v",
            ),
        ),
    ],
)
def test_parse_data(filename: str, expected_res: backend_module.ParsedBenchmarkName) -> None:
    bench_backend = Backend()
    bench_backend.layout_dimensions = bench_backend.read_layout_dimensions_from_json(TARGET_LOCATION)
    assert bench_backend.parse_data(filename) == expected_res


def test_prepare_form_input() -> None:
    form_data = {
        "all_benchmarks": "true",
        "selectBench_1": "MUX 2:1",
        "selectBench_2": "XOR 2:1",
        "selectBench_3": "clpl",
        "selectBench_4": "majority",
        "gate": "true",
        "one": "true",
    }

    expected_res = replace(BASE_CONFIGURATION, indices_benchmarks=list(range(1, 5)), gate=True, one=True)
    bench_backend = Backend()
    assert bench_backend.prepare_form_input(form_data) == expected_res


def test_prepare_form_input_uses_exact_field_names() -> None:
    config = Backend.prepare_form_input({"selectBench_1": "MUX 2:1", "wires": "true", "none": "true"})
    assert config.wires
    assert config.none
    assert not config.res
    assert not config.one


def test_read_mntbench_all_zip(benchmark_directory: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        backend_module,
        "handle_github_api_request",
        lambda _url: pytest.fail("A valid local archive must not trigger a network request."),
    )
    bench_backend = Backend()
    assert bench_backend.read_mntbench_all_zip(str(benchmark_directory), skip_question=True)
    previous_archive = bench_backend.mntbench_all_zip
    assert bench_backend.read_mntbench_all_zip(str(benchmark_directory), skip_question=True)
    assert previous_archive is not None
    assert previous_archive.fp is None


def test_invalid_local_archive_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "MNTBench_all.zip").write_bytes(b"not a zip")

    def missing_package(_package: str) -> str:
        raise metadata.PackageNotFoundError

    monkeypatch.setattr("mnt.bench.backend.metadata.version", missing_package)
    assert not Backend().read_mntbench_all_zip(str(tmp_path), skip_question=True)
    assert "Local benchmark archive is invalid." in capsys.readouterr().out


@pytest.mark.parametrize("local_content", [None, "old"], ids=["empty-placeholder", "stale-archive"])
def test_refreshes_archive_from_older_release_asset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, local_content: str | None
) -> None:
    download_urls: list[str] = []
    with ZipFile(tmp_path / "MNTBench_all.zip", mode="w") as archive:
        if local_content is not None:
            archive.writestr("mux21.v", local_content)
    releases = [
        {"tag_name": "not-a-version", "assets": []},
        {"tag_name": "v0.3.10", "assets": []},
        {
            "tag_name": "v0.4.0",
            "assets": [
                {
                    "name": "MNTBench_all.zip",
                    "browser_download_url": "https://example.com/future-benchmarks",
                    "size": 42,
                }
            ],
        },
        {
            "tag_name": "v0.3.8",
            "assets": [
                {"name": "notes.txt", "browser_download_url": "https://example.com/notes", "size": 1},
                {
                    "name": "MNTBench_all.zip",
                    "browser_download_url": "https://example.com/benchmarks",
                    "size": 42,
                },
            ],
        },
        {
            "tag_name": "v0.3.9",
            "assets": [
                {
                    "name": "MNTBench_all.zip",
                    "browser_download_url": "https://example.com/latest-benchmarks",
                    "size": 42,
                }
            ],
        },
    ]
    monkeypatch.setattr("mnt.bench.backend.metadata.version", lambda _package: "0.3.10")
    monkeypatch.setattr(
        backend_module,
        "handle_github_api_request",
        lambda _url: SimpleNamespace(json=lambda: releases),
    )

    bench_backend = Backend()
    expected_size = len(b"fixture:mux21.v")
    bench_backend.layout_dimensions = [{"mux21.v": {"size_uncompressed": expected_size}}]

    def download(target_location: str, download_url: str, expected_sizes: dict[str, int] | None) -> None:
        download_urls.append(download_url)
        assert expected_sizes == {"mux21.v": expected_size}
        with ZipFile(Path(target_location) / "MNTBench_all.zip", mode="w") as archive:
            archive.writestr("mux21.v", "fixture:mux21.v")

    monkeypatch.setattr(bench_backend, "handle_downloading_benchmarks", download)
    assert bench_backend.read_mntbench_all_zip(str(tmp_path), skip_question=True)
    assert download_urls == ["https://example.com/latest-benchmarks"]


def test_download_rejects_mismatched_archive_without_replacing_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "MNTBench_all.zip"
    with ZipFile(destination, mode="w") as archive:
        archive.writestr("mux21.v", "current")
    original_archive = destination.read_bytes()

    incoming = BytesIO()
    with ZipFile(incoming, mode="w") as archive:
        archive.writestr("mux21.v", "wrong")

    class FakeResponse:
        def __init__(self) -> None:
            self.headers = {"content-length": str(len(incoming.getvalue()))}

        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        def iter_content(self, chunk_size: int) -> list[bytes]:
            assert chunk_size == 1024 * 1024
            return [incoming.getvalue()]

    monkeypatch.setattr("mnt.bench.backend.requests.get", lambda *_args, **_kwargs: FakeResponse())
    with pytest.raises(BadZipFile, match="does not match"):
        Backend.handle_downloading_benchmarks(
            str(tmp_path),
            "https://example.com/benchmarks",
            {"mux21.v": len(b"expected")},
        )

    assert destination.read_bytes() == original_archive
    assert not destination.with_suffix(".zip.part").exists()

    Backend.handle_downloading_benchmarks(
        str(tmp_path),
        "https://example.com/benchmarks",
        {"mux21.v": len(b"wrong")},
    )
    with ZipFile(destination) as archive:
        assert archive.read("mux21.v") == b"wrong"


def test_create_database(initialized_backend: Backend) -> None:
    input_data = replace(BASE_CONFIGURATION, gate=True, one=True)
    selected_files = initialized_backend.get_selected_file_paths(initialized_backend.get_updated_table(input_data))
    assert set(selected_files) == set(BENCHMARK_FILENAMES) - {"mux21.v"}


def test_filter_multiple_algorithms(initialized_backend: Backend) -> None:
    input_data = replace(
        BASE_CONFIGURATION,
        gate=True,
        one=True,
        twoddwave=True,
        exact=True,
        nanoplacer=True,
        area=True,
    )
    table = initialized_backend.get_updated_table(input_data)
    assert set(table["physical_design_algorithm"]) == {"exact", "nanoplacer"}


def test_filter_multiple_gold_costs(initialized_backend: Backend) -> None:
    input_data = replace(
        BASE_CONFIGURATION,
        gate=True,
        one=True,
        twoddwave=True,
        gold=True,
        area=True,
        wires=True,
    )
    table = initialized_backend.get_updated_table(input_data)
    assert set(table["cost"]) == {"area", "wires"}


@pytest.mark.parametrize(
    ("configuration", "expected_files"),
    [
        (replace(BASE_CONFIGURATION, gate=True, one=True, best=True), {"mux21_ONE_BEST.fgl"}),
        (replace(BASE_CONFIGURATION, network=True), {"mux21.v"}),
        (
            replace(
                BASE_CONFIGURATION,
                gate=True,
                one=True,
                twoddwave=True,
                ortho=True,
                optimized=True,
                ordered=True,
                none=True,
            ),
            {"mux21_ONE_2DDWave_ortho_Opt_Ord_none.fgl"},
        ),
    ],
)
def test_filter_special_cases(
    initialized_backend: Backend,
    configuration: BenchmarkConfiguration,
    expected_files: set[str],
) -> None:
    table = initialized_backend.get_updated_table(configuration)
    assert set(initialized_backend.get_selected_file_paths(table)) == expected_files


def test_filter_empty_database_and_selection(initialized_backend: Backend) -> None:
    assert Backend().get_updated_table(BASE_CONFIGURATION).empty
    assert initialized_backend.get_updated_table(BASE_CONFIGURATION).empty


def test_streaming_zip(initialized_backend: Backend, monkeypatch: pytest.MonkeyPatch) -> None:
    assert initialized_backend.mntbench_all_zip is not None
    monkeypatch.setattr(
        initialized_backend.mntbench_all_zip,
        "read",
        lambda *_args, **_kwargs: pytest.fail("Archive members must be streamed instead of read into memory."),
    )
    selected_files = [
        "mux21_ONE_BEST.fgl",
        "mux21_ONE_2DDWave_exact_UnOpt_UnOrd_area.fgl",
        "mux21.v",
    ]
    archive_bytes = b"".join(initialized_backend.generate_zip_ephemeral_chunks(selected_files))
    with ZipFile(BytesIO(archive_bytes)) as archive:
        assert archive.namelist() == selected_files
        for filename in selected_files:
            assert archive.read(filename) == f"fixture:{filename}".encode()

    with pytest.raises(KeyError):
        list(initialized_backend.generate_zip_ephemeral_chunks(["not_existing_file.fgl"]))


@pytest.fixture
def flask_client(benchmark_directory: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[FlaskClient]:
    monkeypatch.setattr(
        backend_module,
        "handle_github_api_request",
        lambda _url: pytest.fail("Server startup must use the valid local archive."),
    )
    monkeypatch.setattr(
        Backend, "read_layout_dimensions_from_json", staticmethod(lambda _path: FIXTURE_LAYOUT_DIMENSIONS)
    )
    Server(skip_question=True, activate_logging=False, target_location=str(benchmark_directory))

    with app.test_client() as client:
        yield client


def test_flask_server(flask_client: FlaskClient) -> None:
    with resources.as_file(resources.files("mnt.bench")) as bench_location:
        for path in ("templates/index.html", "templates/legal.html", "templates/description.html"):
            assert (bench_location / path).is_file()

    for endpoint in (
        "/mntbench/",
        "/mntbench/index",
        "/mntbench/get_pre_gen",
        "/mntbench/download",
        "/mntbench/legal",
        "/mntbench/description",
        "/mntbench/bench.css",
        "/mntbench/bench.js",
    ):
        assert flask_client.get(endpoint).status_code == 200

    html = flask_client.get("/mntbench/").get_data(as_text=True)
    for name in (
        *(f"selectBench_{identifier}" for identifier in range(1, 44)),
        "network",
        "gate",
        "one",
        "bestagon",
        "twoddwave",
        "use",
        "res",
        "esr",
        "row",
        "best-layout",
        "exact",
        "ortho",
        "nanoplacer",
        "gold",
        "post-layout",
        "input-ordering",
        "area",
        "wires",
        "crossings",
        "acp",
        "format",
        "button",
    ):
        assert f'name="{name}"' in html
    assert 'action="/mntbench/download"' in html
    assert 'data-summary-url="/mntbench/get_num_benchmarks"' in html
    assert 'href="/mntbench/bench.css"' in html
    assert 'src="/mntbench/bench.js"' in html

    selection = {"button": "submit", "selectBench_1": "MUX 2:1", "network": "true"}
    response = flask_client.post("/mntbench/download", data=selection)
    with ZipFile(BytesIO(response.data)) as archive:
        assert archive.namelist() == ["mux21.v"]

    response = flask_client.post("/mntbench/get_num_benchmarks", data=selection)
    summary = response.get_json()
    assert summary["num_selected"] == 1
    assert "mux21.v" in summary["table"]
    assert summary["size_compressed"]
    assert summary["size_uncompressed"]


def test_qca_wordmark(flask_client: FlaskClient) -> None:
    url = "/mntbench/qca_wordmark.svg"
    assert f'src="{url}"' in flask_client.get("/mntbench/").get_data(as_text=True)
    response = flask_client.get(url)
    assert response.status_code == 200
    assert response.mimetype == "image/svg+xml"
    svg = ET.fromstring(response.data)
    ns = {"svg": "http://www.w3.org/2000/svg"}
    words = svg.findall("svg:g", ns)
    assert [word.attrib["data-word"] for word in words] == ["MNT", "BENCH"]
    for word in words:
        assert "".join(letter.attrib["data-letter"] for letter in word) == word.attrib["data-word"]

    symbols = svg.findall("svg:defs/svg:symbol", ns)
    assert len(symbols) == 2
    for symbol in symbols:
        dots = symbol.findall("svg:circle", ns)
        assert len(dots) == 4
        assert {(int(dot.attrib["cx"]), int(dot.attrib["cy"])) for dot in dots} == {
            (8, 8),
            (8, 20),
            (20, 8),
            (20, 20),
        }
        filled = [(int(dot.attrib["cx"]), int(dot.attrib["cy"])) for dot in dots if dot.attrib["fill"] != "none"]
        assert len(filled) == 2
        assert set(filled) in ({(8, 8), (20, 20)}, {(8, 20), (20, 8)})

    letter_b = svg.find(".//svg:g[@data-letter='B']", ns)
    assert letter_b is not None
    expected_cells = {
        (column * 32, row * 32)
        for row, pattern in enumerate(("11110", "10001", "10001", "11110", "10001", "10001", "11110"))
        for column, cell in enumerate(pattern)
        if cell == "1"
    }
    cells = letter_b.findall("svg:use", ns)
    assert len(cells) == len(expected_cells)
    assert {(int(cell.attrib["x"]), int(cell.attrib["y"])) for cell in cells} == expected_cells


def test_qca_wordmark_motion(flask_client: FlaskClient) -> None:
    svg = ET.fromstring(flask_client.get("/mntbench/qca_wordmark.svg").data)
    ns = {"svg": "http://www.w3.org/2000/svg"}
    css = svg.findtext("svg:style", namespaces=ns) or ""
    assert css.strip().startswith("@media (prefers-reduced-motion: no-preference)")
    assert "animation: cell-wake 1100ms ease-out backwards;" in css
    assert "infinite" not in css
    for letter in svg.findall("svg:g/svg:g", ns):
        position = letter.attrib["transform"].removeprefix("translate(").removesuffix(")")
        delay = sum(map(int, position.split()))
        assert letter.attrib["style"] == f"--letter-delay: {delay}ms"
        for cell in letter.findall("svg:use", ns):
            assert delay + int(cell.attrib["x"]) + int(cell.attrib["y"]) + 1100 < 3000
            for axis, variable in (("x", "column"), ("y", "row")):
                coordinate = int(cell.attrib[axis])
                if coordinate:
                    assert f'use[{axis}="{coordinate}"] {{ --{variable}-delay: {coordinate}ms; }}' in css


def test_guide_illustrations(flask_client: FlaskClient) -> None:
    illustrations = (
        "abstraction_level.png",
        "gate_library.png",
        "clocking_scheme.png",
        "physical_design_algorithm.png",
        "optimization_algorithm.png",
    )
    html = flask_client.get("/mntbench/description").get_data(as_text=True)
    assert html.count("data-illustration") == len(illustrations)
    assert 'id="illustration-dialog"' in html
    assert 'id="illustration-image"' in html
    assert 'aria-label="Close illustration"' in html
    assert "data-close-dialog" in html
    for filename in illustrations:
        url = f"/mntbench/{filename}"
        assert f'href="{url}"' in html
        response = flask_client.get(url)
        assert response.status_code == 200
        assert response.mimetype == "image/png"
        assert response.data.startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.parametrize(
    ("format_name", "content_type", "extension"),
    [
        ("csv", "text/csv", "csv"),
        ("excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"),
        ("json", "application/json", "json"),
    ],
)
def test_table_exports(flask_client: FlaskClient, format_name: str, content_type: str, extension: str) -> None:
    response = flask_client.post(
        "/mntbench/download",
        data={"button": "submitTable", "format": format_name, "selectBench_1": "true", "network": "true"},
    )
    assert response.status_code == 200
    assert response.mimetype == content_type
    assert response.headers["Content-Disposition"] == f"attachment; filename=table.{extension}"

    if format_name == "excel":
        table = pd.read_excel(BytesIO(response.data))
    elif format_name == "csv":
        table = pd.read_csv(StringIO(response.get_data(as_text=True)))
    else:
        table = pd.read_json(StringIO(response.get_data(as_text=True)), lines=True)

    assert table["Filename"].to_list() == ["mux21.v"]
    assert table["Benchmark Function"].to_list() == ["MUX 2:1"]
    assert table["Abstraction Level"].to_list() == ["Network"]


def test_empty_selection_and_export_error(flask_client: FlaskClient) -> None:
    response = flask_client.post("/mntbench/get_num_benchmarks", data={})
    assert response.get_json()["num_selected"] == 0

    for response in (
        flask_client.get("/mntbench/download"),
        flask_client.post("/mntbench/download", data={"button": "submit"}),
    ):
        assert response.status_code == 200
        assert 'id="benchmark_form"' in response.get_data(as_text=True)

    response = flask_client.post("/mntbench/download", data={"button": "submitTable", "format": "csv"})
    table = pd.read_csv(StringIO(response.get_data(as_text=True)))
    assert "Filename" in table.columns
    assert table.empty

    response = flask_client.post(
        "/mntbench/download", data={"button": "submitTable", "format": "<script>alert(1)</script>"}
    )
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Unsupported format: &lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html


def test_logging_uses_target_location(benchmark_directory: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    configured_log_files: list[Path] = []

    def record_logging_config(*, filename: Path, level: int) -> None:
        assert level > 0
        configured_log_files.append(filename)

    monkeypatch.setattr("mnt.bench.main.logging.basicConfig", record_logging_config)
    monkeypatch.setattr(
        Backend, "read_layout_dimensions_from_json", staticmethod(lambda _path: FIXTURE_LAYOUT_DIMENSIONS)
    )
    Server(skip_question=True, activate_logging=True, target_location=str(benchmark_directory))
    assert configured_log_files == [benchmark_directory / "downloads.log"]
    with app.test_client() as client:
        assert client.get("/mntbench/get_pre_gen").status_code == 200


def test_cli_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit, match="0"):
        main(["--help"])
    assert "Run the local MNT Bench viewer" in capsys.readouterr().out


def test_cli_starts_server_with_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    server_arguments: list[tuple[str, bool, bool]] = []
    run_arguments: list[tuple[bool, int]] = []

    def create_server(target_location: str, skip_question: bool, activate_logging: bool) -> None:
        server_arguments.append((target_location, skip_question, activate_logging))

    def run_server(*, debug: bool, port: int) -> None:
        run_arguments.append((debug, port))

    monkeypatch.setattr(main_module, "Server", create_server)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(app, "run", run_server)

    main(["--skip-question", "--activate-logging", "--debug"])

    assert server_arguments == [(str(tmp_path / ".mntbench"), True, True)]
    assert run_arguments == [(True, 5001)]
