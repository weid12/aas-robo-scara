import json
import os
import sqlite3
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from typing import Dict, Any


BASE_DIR = Path(__file__).resolve().parent.parent  # repo root (test_aas_25_10)
WEB_DIR = Path(__file__).resolve().parent
LATEST_PATH = BASE_DIR / "opcua_client" / "latest_data.json"
DB_PATH = BASE_DIR / "data" / "aas_history.sqlite3"
SUBMODELS_DIR = BASE_DIR / "aas-submodels"
EXPORTS_DIR = BASE_DIR / "exports"


def _json_response(handler: SimpleHTTPRequestHandler, obj: Any, status: int = 200):
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _read_latest() -> Dict[str, Any]:
    if not LATEST_PATH.exists():
        return {}
    with open(LATEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _db_connect():
    if not DB_PATH.exists():
        return None
    return sqlite3.connect(DB_PATH)


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        # Serve files from WEB_DIR
        p = super().translate_path(path)
        rel = Path(urlparse(path).path.lstrip("/"))
        target = (WEB_DIR / rel).resolve()
        # Default to index.html for root
        if path in ("/", ""):
            target = WEB_DIR / "index.html"
        return str(target)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/latest":
            return _json_response(self, _read_latest())
        if parsed.path == "/download/aasx":
            # Build a standards-compliant AASX if possible; otherwise fallback to snapshot zip
            try:
                pkg_path = self._build_full_aasx()
            except Exception:
                try:
                    pkg_path = self._build_snapshot_aasx()
                except FileNotFoundError:
                    self.send_error(404, "Submodels folder not found")
                    return
            data = pkg_path.read_bytes()
            filename = pkg_path.name
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f"attachment; filename=\"{filename}\"")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if parsed.path == "/api/paths":
            con = _db_connect()
            if con is None:
                return _json_response(self, {"paths": []})
            try:
                cur = con.cursor()
                cur.execute(
                    "SELECT DISTINCT submodel_name, element_path FROM timeseries ORDER BY submodel_name, element_path LIMIT 500"
                )
                items = [
                    {"submodel": r[0], "path": r[1]} for r in cur.fetchall()
                ]
                return _json_response(self, {"paths": items})
            finally:
                con.close()
        if parsed.path == "/api/timeseries":
            qs = parse_qs(parsed.query)
            submodel = (qs.get("submodel") or [None])[0]
            path = (qs.get("path") or [None])[0]
            limit = int((qs.get("limit") or ["200"])[0])
            if not submodel or not path:
                return _json_response(self, {"error": "missing submodel or path"}, 400)
            con = _db_connect()
            if con is None:
                return _json_response(self, {"rows": []})
            try:
                cur = con.cursor()
                cur.execute(
                    """
                    SELECT value, created_at
                    FROM timeseries
                    WHERE submodel_name = ? AND element_path = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (submodel, path, limit),
                )
                rows = cur.fetchall()
                rows.reverse()
                return _json_response(
                    self, {"rows": [{"t": t, "v": v} for (v, t) in rows]}
                )
            finally:
                con.close()
        # Fallback to static files
        return super().do_GET()

    def _build_snapshot_aasx(self) -> Path:
        """
        Create a simple .aasx by zipping JSON files under SUBMODELS_DIR.
        This is not fully spec-compliant, but serves as a quick snapshot.
        """
        if not SUBMODELS_DIR.exists():
            raise FileNotFoundError("submodels directory missing")
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

        from datetime import datetime
        import zipfile

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = EXPORTS_DIR / f"submodels_{ts}.aasx"

        with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # include all submodel JSONs
            for p in sorted(SUBMODELS_DIR.glob("*.json")):
                zf.write(p, arcname=f"aas-submodels/{p.name}")
            # also include the latest snapshot if present
            if LATEST_PATH.exists():
                zf.write(LATEST_PATH, arcname="latest_data.json")
        return out_path

    def _build_full_aasx(self) -> Path:
        """Generate a spec-compliant AASX using aas-core3 if available."""
        try:
            from aas_export.export_aasx import export_full_aasx  # type: ignore
        except Exception as e:
            raise RuntimeError("aas-core3 export not available") from e

        from datetime import datetime

        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = EXPORTS_DIR / f"aas_env_{ts}.aasx"
        return export_full_aasx(SUBMODELS_DIR, out_path)


def main(host: str = "127.0.0.1", port: int = 8000):
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Web dashboard em http://{host}:{port}/  (Ctrl+C para parar)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    host = os.getenv("AAS_WEB_HOST", "127.0.0.1")
    try:
        port = int(os.getenv("AAS_WEB_PORT", "8000"))
    except ValueError:
        port = 8000
    main(host, port)
