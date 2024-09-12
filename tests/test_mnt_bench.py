from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from mnt.bench import Backend, BenchmarkConfiguration, Server, backend
from mnt.bench.main import app

if TYPE_CHECKING or sys.version_info >= (3, 10, 0):  # pragma: no cover
    from importlib import resources
else:
    import importlib_resources as resources


target_location = str(resources.files("mnt.bench") / "static" / "files")


@pytest.mark.parametrize(
    ("filename", "expected_res"),
    [
        (
            "mux21_ONE_2DDWave_exact_UnOpt_UnOrd_area.fgl",
            backend.ParsedBenchmarkName(
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
            backend.ParsedBenchmarkName(
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
            backend.ParsedBenchmarkName(
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
            backend.ParsedBenchmarkName(
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
            "clpl.v",
            backend.ParsedBenchmarkName(
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
def test_parse_data(filename: str, expected_res: backend.ParsedBenchmarkName) -> None:
    backend = Backend()
    backend.layout_dimensions = backend.read_layout_dimensions_from_json(target_location)
    assert backend.parse_data(filename) == expected_res


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

    expected_res = BenchmarkConfiguration(
        indices_benchmarks=list(range(1, 5)),
        gate=True,
        network=False,
        one=True,
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
    backend = Backend()
    assert backend.prepare_form_input(form_data) == expected_res


bench = resources.files("mnt.bench")


def test_read_mntbench_all_zip() -> None:
    backend = Backend()
    with resources.as_file(bench) as bench_path:
        target_location = str(bench_path / "static/files")
    assert backend.read_mntbench_all_zip(skip_question=True, target_location=target_location, test=True)


def test_create_database() -> None:
    backend = Backend()
    backend.layout_dimensions = backend.read_layout_dimensions_from_json(target_location)

    res_zip = backend.read_mntbench_all_zip(
        skip_question=True, target_location=str(resources.files("mnt.bench") / "static" / "files"), test=True
    )
    assert res_zip

    assert backend.database is None
    backend.init_database()

    input_data = BenchmarkConfiguration(
        indices_benchmarks=[4],
        gate=True,
        network=False,
        one=True,
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

    res = backend.get_selected_file_paths(backend.get_updated_table(input_data))
    assert isinstance(res, list)
    assert len(res) > 3


def test_streaming_zip() -> None:
    backend = Backend()
    backend.read_mntbench_all_zip(
        skip_question=True, target_location=str(resources.files("mnt.bench") / "static" / "files"), test=True
    )
    res = backend.generate_zip_ephemeral_chunks(
        filenames=["mux21_ONE_BEST.fgl", "xor2_ONE_BEST.fgl", "xor2_ONE_2DDWave_gold_UnOpt_UnOrd_wires.fgl"]
    )
    assert list(res)

    with pytest.raises(KeyError):
        assert not list(backend.generate_zip_ephemeral_chunks(filenames=["not_existing_file.fgl"]))


def test_flask_server() -> None:
    with resources.as_file(bench) as bench_path:
        bench_location = bench_path
    target_location = str(bench_location / "static/files")

    Server(
        skip_question=True,
        activate_logging=False,
        target_location=target_location,
    )

    paths_to_check = [
        "static/files/MNTBench_all.zip",
        "templates/index.html",
        "templates/legal.html",
        "templates/description.html",
    ]
    for path in paths_to_check:
        assert (bench_location / path).is_file()

    with app.test_client() as c:
        success_code = 200
        links_to_check = [
            "/mntbench/index",
            "/mntbench/download",
            "/mntbench/legal",
            "/mntbench/description",
        ]
        for link in links_to_check:
            assert c.get(link).status_code == success_code
