"""One browser workflow against the real app and the existing tiny archive fixture."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING
from zipfile import ZipFile

import pytest
from playwright.sync_api import expect
from werkzeug.serving import make_server

from mnt.bench.main import app

if TYPE_CHECKING:
    from collections.abc import Iterator

    from flask.testing import FlaskClient
    from playwright.sync_api import Page

pytest_plugins = ["test_mnt_bench"]


@pytest.fixture
def live_url(flask_client: FlaskClient) -> Iterator[str]:  # noqa: ARG001
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/mntbench/"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_filter_and_download(page: Page, live_url: str) -> None:
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(live_url)
    expect(page.locator("#result-count")).to_have_text("8")
    page.locator("#clear-circuits").click()
    page.locator("#selectBench_1").check()
    page.locator("#gate").uncheck()
    expect(page.locator("#result-count")).to_have_text("1")
    with page.expect_download() as download:
        page.locator("#download-button").click()
    download_path = download.value.path()
    assert download_path is not None
    with ZipFile(download_path) as archive:
        assert archive.namelist() == ["mux21.v"]
        assert archive.read("mux21.v") == b"fixture:mux21.v"
    assert not errors
