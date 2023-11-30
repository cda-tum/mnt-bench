from __future__ import annotations

import io
import logging
import os
import sys
from datetime import datetime
from typing import TYPE_CHECKING

import humanize  # type: ignore[import-not-found]
import pandas as pd
from flask import Flask, cli, jsonify, make_response, render_template, request, send_from_directory

from mnt.bench.backend import Backend

if TYPE_CHECKING or sys.version_info < (3, 10, 0):  # pragma: no cover
    import importlib_resources as resources
else:
    from importlib import resources

if TYPE_CHECKING:  # pragma: no cover
    from flask import Response


class Server:
    def __init__(
        self,
        target_location: str,
        skip_question: bool = False,
        activate_logging: bool = False,
    ):
        self.backend = Backend()

        self.target_location = target_location
        if not os.access(self.target_location, os.W_OK):
            msg = "target_location is not writable. Please specify a different path."
            raise RuntimeError(msg)

        res_zip = self.backend.read_mntbench_all_zip(self.target_location, skip_question)
        if not res_zip:
            msg = "Error while reading the MNTBench_all.zip file."
            raise RuntimeError(msg)

        self.backend.layout_dimensions = self.backend.read_layout_dimensions_from_json(
            str(resources.files("mnt.bench") / "static" / "files")
        )
        self.backend.init_database()
        if self.backend.database is None:
            msg = "Error while initializing the database."
            raise RuntimeError(msg)

        self.activate_logging = activate_logging

        if self.activate_logging:
            logging.basicConfig(filename="/local/mntbench/downloads.log", level=logging.INFO)
        global SERVER  # noqa: PLW0603
        SERVER = self


app = Flask(__name__, static_url_path="/mntbench")
SERVER: Server = None  # type: ignore[assignment]
PREFIX = "/mntbench/"


@app.route(f"{PREFIX}/", methods=["POST", "GET"])
@app.route(f"{PREFIX}/index", methods=["POST", "GET"])
def index() -> str:
    """Return the index.html file together with the benchmarks and nonscalable benchmarks."""
    return render_template(
        "index.html",
        trindade=SERVER.backend.trindade,
        fontes=SERVER.backend.fontes,
        iscas=SERVER.backend.iscas,
        epfl=SERVER.backend.epfl,
        tables=[pd.DataFrame().to_html(classes="data", header="true", index=False)],
    )


@app.route(f"{PREFIX}/get_pre_gen", methods=["POST", "GET"])
def download_pre_gen_zip() -> Response:
    filename = "MNTBench_all.zip"

    if SERVER.activate_logging:
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        app.logger.info("###### Start ######")
        app.logger.info("Timestamp: %s", timestamp)
        headers = str(request.headers)
        headers = headers.replace("\r\n", "").replace("\n", "")
        app.logger.info("Headers: %s", headers)
        app.logger.info("Download of pre-generated zip")
        app.logger.info("###### End ######")

    return send_from_directory(
        SERVER.target_location,
        filename,
        as_attachment=True,
        mimetype="application/zip",
        download_name="MNTBench_all.zip",
    )


@app.route(f"{PREFIX}/download", methods=["POST", "GET"])
def download_data() -> str | Response:
    """Triggers the downloading process of all benchmarks according to the user's input."""
    if request.method == "POST":
        selected_action = request.form["button"]
        if selected_action == "submit":
            data = request.form
            prepared_data = SERVER.backend.prepare_form_input(data)
            table = SERVER.backend.get_updated_table(prepared_data)
            file_paths = SERVER.backend.get_selected_file_paths(table)
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

            if SERVER.activate_logging:
                app.logger.info("###### Start ######")
                app.logger.info("Timestamp: %s", timestamp)
                headers = str(request.headers)
                headers = headers.replace("\r\n", "").replace("\n", "")
                app.logger.info("Headers: %s", headers)
                app.logger.info("Prepared_data: %s", prepared_data)
                app.logger.info("Download started: %s", len(file_paths))
                app.logger.info("###### End ######")

            if file_paths:
                return app.response_class(  # type: ignore[no-any-return]
                    SERVER.backend.generate_zip_ephemeral_chunks(file_paths),
                    mimetype="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="MNTBench_{timestamp}.zip"'},
                    direct_passthrough=True,
                )

        elif selected_action == "submitTable":
            try:
                prepared_data = SERVER.backend.prepare_form_input(request.form)
                raw_table = SERVER.backend.get_updated_table(prepared_data)
                table = SERVER.backend.prettify_table(raw_table)

                # Get the selected format from the form
                format_type = request.form["format"]

                # Convert DataFrame to the selected format
                if format_type == "csv":
                    content_type = "text/csv"
                    file_extension = "csv"
                    file_data = table.to_csv(index=False)
                elif format_type == "excel":
                    content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    file_extension = "xlsx"
                    # Use BytesIO to create an in-memory Excel file
                    excel_file = io.BytesIO()
                    table.to_excel(excel_file, index=False, engine="openpyxl")  # Specify the engine as openpyxl
                    file_data = excel_file.getvalue()
                elif format_type == "json":
                    content_type = "application/json"
                    file_extension = "json"
                    file_data = table.to_json(orient="records", lines=True)
                else:
                    e = f"Unsupported format: {format_type}"
                    return render_template("error.html", error_message=str(e))

                # Set up the response
                response = make_response(file_data)
                response.headers["Content-Type"] = content_type
                response.headers["Content-Disposition"] = f"attachment; filename=table.{file_extension}"

                return response
            except Exception as e:
                return render_template("error.html", error_message=str(e))
        else:
            return render_template("error.html", error_message="Invalid button selected!")

    return render_template(
        "index.html",
        trindade=SERVER.backend.trindade,
        fontes=SERVER.backend.fontes,
        iscas=SERVER.backend.iscas,
        epfl=SERVER.backend.epfl,
        tables=[pd.DataFrame().to_html(classes="data", header="true", index=False)],
    )


@app.route(f"{PREFIX}/legal")
def legal() -> str:
    """Return the legal.html file."""
    return render_template("legal.html")


@app.route(f"{PREFIX}/description")
def description() -> str:
    """Return the description.html file in which the file formats are described."""
    return render_template("description.html")


@app.route(f"{PREFIX}/get_num_benchmarks", methods=["POST"])
def get_num_benchmarks() -> Response:
    if request.method == "POST":
        data = request.form
        prepared_data = SERVER.backend.prepare_form_input(data)
        raw_table = SERVER.backend.get_updated_table(prepared_data)
        file_paths = SERVER.backend.get_selected_file_paths(raw_table)
        size_compressed = humanize.naturalsize(raw_table["size_compressed"].sum())
        size_uncompressed = humanize.naturalsize(raw_table["size_uncompressed"].sum())
        table = SERVER.backend.prettify_table(raw_table)

        return jsonify(  # type: ignore[no-any-return]
            {
                "num_selected": len(file_paths),
                "table": table.to_html(classes="data", header="true", index=False),
                "size_compressed": size_compressed,
                "size_uncompressed": size_uncompressed,
            }
        )
    return jsonify(  # type: ignore[no-any-return]
        {
            "num_selected": 0,
            "table": pd.DataFrame().to_html(classes="data", header="true", index=False),
            "size_compressed": 0,
            "size_uncompressed": 0,
        }
    )


def start_server(
    skip_question: bool = False,
    activate_logging: bool = False,
    target_location: str | None = None,
    debug_flag: bool = False,
) -> None:
    if not target_location:
        target_location = str(resources.files("mnt.bench") / "static" / "files")

    Server(
        target_location=target_location,
        skip_question=skip_question,
        activate_logging=activate_logging,
    )
    print(
        "Server is hosted at: http://127.0.0.1:5001" + PREFIX + ".",
        "To stop it, interrupt the process (e.g., via CTRL+C). \n",
    )

    # This line avoid the startup-message from flask
    cli.show_server_banner = lambda *_args: None

    if not activate_logging:
        log = logging.getLogger("werkzeug")
        log.disabled = True

    app.run(debug=debug_flag, port=5001)


if __name__ == "__main__":
    start_server()
