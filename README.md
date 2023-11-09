[![PyPI](https://img.shields.io/pypi/v/mnt.bench?logo=pypi&style=flat-square)](https://pypi.org/project/mnt.bench/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![CI](https://img.shields.io/github/actions/workflow/status/cda-tum/MNTBench/coverage.yml?branch=main&style=flat-square&logo=github&label=coverage)](https://github.com/cda-tum/mnt-bench/actions/workflows/coverage.yml)
[![Bindings](https://img.shields.io/github/actions/workflow/status/cda-tum/MNTBench/deploy.yml?branch=main&style=flat-square&logo=github&label=python)](https://github.com/cda-tum/mnt-bench/actions/workflows/deploy.yml)
[![codecov](https://img.shields.io/codecov/c/github/cda-tum/mnt-bench?style=flat-square&logo=codecov)](https://codecov.io/gh/cda-tum/mnt-bench)

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/cda-tum/mnt-bench/main/img/mnt_light.svg" width="60%">
  <img src="https://raw.githubusercontent.com/cda-tum/mnt-bench/main/img/mnt_dark.svg" width="60%">
</picture>
</p>

# MNT Bench: Layout Library for Field-coupled Nanocomputing Circuits

MNT Bench is a field-coupled nanocomputing circuit benchmark suite for multiple gate libraries and clocking schemes.

MNT Bench is part of the Munich Nanotech Toolkit (MNT) developed by the [Chair for Design Automation](https://www.cda.cit.tum.de/) at the [Technical University of Munich](https://www.tum.de/) and is hosted at [https://www.cda.cit.tum.de/mntbench/](https://www.cda.cit.tum.de/mntbench/).

This documentation explains how to use MNT Bench to filter and download benchmarks.

## Benchmark Selection

So far, the functions from the following benchmark sets are implemented and provided:

1. [Trindade16]()
2. [Fontes18]()
3. [ISCAS85]()
4. [EPFL]()

See the [benchmark description](https://www.cda.cit.tum.de/mntbench/benchmark_description) for further details on the individual benchmarks.

## Gate Libraries

So far, MNT Bench supports the following native gate-sets:

1. [QCA ONE]() gate set: _\[AND, OR, NOT, BUF\]_
2. [Bestagon]() gate set: _\[AND, NAND, OR, NOR, XOR, XNOR, NOT, BUF\]_

## Clocking Schemes

Most of the layouts are available for any of the following clocking schemes:

1. [2DDWave]()
2. [USE]()
3. [RES]()
4. [ESR]()
5. [ROW]()

# Repository Structure

- src/mnt/: main source directory
  - bench: Directory for the MNT Bench package
  - benchviewer: Directory for the webpage (which can be started locally and is also hosted at
    [https://www.cda.cit.tum.de/mntbench/](https://www.cda.cit.tum.de/mntbench/))
- tests: Directory for the tests for MNT Bench

# Repository Usage

There are three ways how to use this benchmark suite:

1. Via the webpage hosted at [https://www.cda.cit.tum.de/mntbench/](https://www.cda.cit.tum.de/mntbench/)
2. Via the pip package `mnt.bench`
3. Directly via this repository

Since the first way is rather self-explanatory, the other two ways are explained in more detail in the following.

## Usage via pip package

MNT Bench is available via [PyPI](https://pypi.org/project/mnt.bench/)

```console
(venv) $ pip install mnt.bench
```

### Locally hosting the MNT Bench Viewer

Additionally, this python package includes the same webserver used for the hosting of the
[MNT Bench webpage](https://www.cda.cit.tum.de/mntbench).

After the `mnt.bench` Python package is installed via

```console
(venv) $ pip install mnt.bench
```

the MNT Bench Viewer can be started from the terminal via

```console
(venv) $ mnt.bench
```

This first searches for the most recent version of the benchmark files on GitHub and offers to download them.
Afterwards, the webserver is started locally.

## Usage directly via this repository

For that, the repository must be cloned and installed:

```
git clone https://github.com/cda-tum/mnt-bench.git
cd mnt-bench
pip install .
```

Afterwards, the package can be used as described [above](#Usage via pip package).
