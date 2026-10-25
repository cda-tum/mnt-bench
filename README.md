[![PyPI](https://img.shields.io/pypi/v/mnt.bench?logo=pypi&style=flat-square)](https://pypi.org/project/mnt.bench/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![CI](https://img.shields.io/github/actions/workflow/status/cda-tum/mnt-bench/coverage.yml?branch=main&style=flat-square&logo=github&label=coverage)](https://github.com/cda-tum/mnt-bench/actions/workflows/coverage.yml)
[![Bindings](https://img.shields.io/github/actions/workflow/status/cda-tum/mnt-bench/deploy.yml?branch=main&style=flat-square&logo=github&label=python)](https://github.com/cda-tum/mnt-bench/actions/workflows/deploy.yml)
[![codecov](https://img.shields.io/codecov/c/github/cda-tum/mnt-bench?style=flat-square&logo=codecov)](https://codecov.io/gh/cda-tum/mnt-bench)

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/cda-tum/mnt-bench/main/img/mnt_light.svg" width="60%">
  <img src="https://raw.githubusercontent.com/cda-tum/mnt-bench/main/img/mnt_dark.svg" width="60%" alt="Munich Nanotech Toolkit logo">
</picture>
</p>

# MNT Bench: Layout Library for Field-coupled Nanocomputing Circuits

MNT Bench is a field-coupled nanocomputing circuit benchmark suite for multiple gate libraries and clocking schemes.

MNT Bench is part of the Munich Nanotech Toolkit (MNT) developed by the [Chair for Design Automation](https://www.cda.cit.tum.de/) at the [Technical University of Munich](https://www.tum.de/) and is hosted at [https://www.cda.cit.tum.de/mntbench/](https://www.cda.cit.tum.de/mntbench/).

This documentation explains how to use MNT Bench to filter and download benchmarks.

## Benchmark Selection

So far, the functions from the following benchmark sets are implemented and provided:

1. [Trindade16](https://ieeexplore.ieee.org/document/7724048)
2. [Fontes18](https://ieeexplore.ieee.org/document/8351001)
3. [ISCAS85](https://www.researchgate.net/publication/273775783_A_neutral_netlist_of_10_combinational_benchmark_circuits_and_a_targeted_translator_in_FORTRAN)
4. [EPFL](https://www.epfl.ch/labs/lsi/page-102566-en-html/benchmarks/)

## Gate Libraries

So far, MNT Bench supports the following native gate-sets:

1. [ONE](https://ieeexplore.ieee.org/document/7538997/) (for QCA) gate set: _\[AND, OR, NOT, BUF\]_
2. [Bestagon](https://www.cda.cit.tum.de/files/eda/2022_dac_hexagons_are_the_bestagons.pdf) (for SiDB) gate set: _\[AND, NAND, OR, NOR, XOR, XNOR, NOT, BUF\]_

## Clocking Schemes

Most of the layouts are available for any of the following clocking schemes:

|                                      [2DDWave](https://ieeexplore.ieee.org/document/1717097)                                      |                        [ESR](https://link.springer.com/content/pdf/10.1007/s10470-020-01760-4.pdf)                        |
| :-------------------------------------------------------------------------------------------------------------------------------: | :-----------------------------------------------------------------------------------------------------------------------: |
| <img src="https://raw.githubusercontent.com/cda-tum/mnt-bench/main/src/mnt/bench/static/2ddwave.png" alt="2DDWave" height="200"/> | <img src="https://raw.githubusercontent.com/cda-tum/mnt-bench/main/src/mnt/bench/static/esr.png" alt="ESR" height="200"/> |

|                                    [USE](https://ieeexplore.ieee.org/document/7219390)                                    |                         [RES](https://www.tandfonline.com/doi/abs/10.1080/21681724.2019.1570551)                          |
| :-----------------------------------------------------------------------------------------------------------------------: | :-----------------------------------------------------------------------------------------------------------------------: |
| <img src="https://raw.githubusercontent.com/cda-tum/mnt-bench/main/src/mnt/bench/static/use.png" alt="USE" height="200"/> | <img src="https://raw.githubusercontent.com/cda-tum/mnt-bench/main/src/mnt/bench/static/res.png" alt="RES" height="200"/> |

|                                    [Row](https://ieeexplore.ieee.org/document/573740)                                     |
| :-----------------------------------------------------------------------------------------------------------------------: |
| <img src="https://raw.githubusercontent.com/cda-tum/mnt-bench/main/src/mnt/bench/static/row.png" alt="Row" height="200"/> |

## Repository structure

```text
src/mnt/bench/        Viewer backend, templates, and static assets
tests/                Unit and integration tests
```

## Repository usage

There are three ways how to use this benchmark suite:

1. Via the webpage hosted at [https://www.cda.cit.tum.de/mntbench/](https://www.cda.cit.tum.de/mntbench/)
2. Via the Python package `mnt.bench`, installed with uv or pip
3. Directly via this repository

Since the first way is rather self-explanatory, the other two ways are explained in more detail in the following.

## Usage via the Python package

MNT Bench supports Python 3.10 through 3.14 and is available from [PyPI](https://pypi.org/project/mnt.bench/).

### Recommended: install the viewer with uv

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) 0.13.5 or newer, then run:

```console
uv tool install --python 3.13 mnt.bench
mnt-bench
```

uv manages a separate environment for the viewer; no activation is needed. The explicit Python version keeps the
installation within the supported range, and uv can download Python if it is missing. If the command is not on your
PATH, run `uv tool update-shell` and restart your terminal. To update the installed viewer, run `uv tool upgrade mnt.bench`.

To try the viewer without a persistent tool installation:

```console
uvx --python 3.13 --from mnt.bench mnt-bench
```

The first run installs dependencies; subsequent runs reuse uv's cache. Benchmark data is still stored separately in
`~/.mntbench`. Stop the viewer with Ctrl+C. Open <http://127.0.0.1:5001/mntbench/> in your browser.

### Python library or pip installation

`uv tool install` isolates the application, so it does not make `mnt.bench` importable from your own Python scripts.
For that, install it in your project's environment instead:

```console
uv venv --python 3.13
uv pip install --python .venv mnt.bench
uv run --no-project --python .venv python -c "from mnt.bench.backend import Backend"
```

Standard pip installations remain supported:

```console
python -m venv .venv
source .venv/bin/activate
python -m pip install mnt.bench
```

For fish, activate with `source .venv/bin/activate.fish`; for Windows PowerShell, use `.venv\Scripts\Activate.ps1`.

### Locally hosting the MNT Bench Viewer

Additionally, this python package includes the same webserver used for the hosting of the
[MNT Bench webpage](https://www.cda.cit.tum.de/mntbench).

Start the MNT Bench Viewer from the terminal with either command:

```console
mnt-bench
mnt.bench
```

This first searches for the most recent version of the benchmark files on GitHub and offers to download them.
The archive is stored in `~/.mntbench` by default. Afterwards, the webserver is started locally.
The package includes an empty `MNTBench_all.zip` placeholder; the actual benchmarks are downloaded from the newest
compatible release containing the archive, which may be older than the package release.
Downloaded and cached archives must match the SHA-256 checksum embedded in the package. A failed download is discarded
without replacing the existing archive. When publishing new benchmark data, update `BENCHMARK_ARCHIVE_SHA256` in
`backend.py` from a separately verified release asset; do not trust a checksum fetched alongside the download.

Keep the host's certificate store and each virtual environment's `pip` and `certifi` up to date. MNT Bench requires
`certifi>=2026.10.19`; pip needs its own update because it bundles a separate certificate store. See the
[Python security announcement](https://discuss.python.org/t/information-for-python-users-regarding-emudhra-emsign-ca-certificate-security-incident/109576)
for secure upgrade instructions.

## Usage directly via this repository

Clone and install the repository with:

```console
git clone https://github.com/cda-tum/mnt-bench.git
cd mnt-bench
uv venv --python 3.13
uv pip install --python .venv -e ".[coverage]"
uv run --no-project --python .venv python -m pytest
uv run --no-project --python .venv mnt-bench
```

Afterwards, the package can be used as described [above](#usage-via-the-python-package).
Alternatively, activate a virtual environment and use `python -m pip install -e ".[coverage]"`.
CI builds with uv and the existing setuptools backend, tests wheel installs with uv and source installs with pip,
and checks both `uv tool install` and `uvx`. Publishing and hosted deployments are unchanged.

## Installation, browser, and dependency checks

CI smoke-tests built wheels on macOS ARM and Windows x64 with Python 3.13; the existing Linux jobs cover the
minimum and maximum supported Python versions. One Chromium workflow checks the real interface, and a separate
job audits freshly resolved runtime dependencies (including transitive dependencies) with `pip-audit` on PRs,
main, and weekly. Browser failure traces are retained for seven days; these tests use temporary data only.

To run the browser check locally after creating the development environment:

```console
uv pip install --python .venv pytest-playwright
uv run --no-project --python .venv python -m playwright install chromium
uv run --no-project --python .venv python -m pytest tests/browser_smoke.py
```

The browser test reuses the tiny unit-test archive, not the downloaded benchmark library.
For production upgrades, health checks, and rollback, see [the deployment guide](deploy/README.md).
