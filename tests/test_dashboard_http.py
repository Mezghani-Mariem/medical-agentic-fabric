"""Static HTTP smoke test; this does not execute a browser or colleague backend."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_and_all_local_runtime_resources_serve():
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        paths = ["frontend/", "frontend/style.css", "samples/ecg_valid.csv", "samples/report_valid.txt",
                 "samples/csv_contract_cases.json"]
        paths.extend(path.relative_to(ROOT).as_posix() for path in (ROOT / "frontend").glob("*.js"))
        paths.extend(path.relative_to(ROOT).as_posix() for path in (ROOT / "frontend/fixtures").glob("*.json"))
        for path in paths:
            with urlopen(f"http://127.0.0.1:{server.server_port}/{path}", timeout=5) as response:
                body = response.read()
                assert response.status == 200 and body, path
                if path.endswith(".js"):
                    assert "javascript" in response.headers["Content-Type"], path
                if path == "frontend/":
                    assert "MedTrace" in body.decode("utf-8")
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
