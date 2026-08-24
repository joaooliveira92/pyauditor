from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shlex
import subprocess
import threading
import uuid
import webbrowser
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import parse_qs, urlparse

try:
    from . import inms
except ImportError:  # python3 server.py — run as a script, not a package
    import inms  # ty: ignore[unresolved-import]

LOG = logging.getLogger("wayfinder")
ALLOWED_SUFFIXES = frozenset({".yaml", ".yml", ".css"})
MAX_FILE_BYTES = 2 * 1024 * 1024
COMPETENCE_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
AGENCIES = frozenset({"MinC", "MTur", "both"})
COMMANDS = frozenset({"bootstrap", "measure", "report", "consolidate", "split", "run"})
NEEDS_COMPETENCE = frozenset({"measure", "report", "consolidate", "split", "run"})
NEEDS_ORGAO = frozenset({"bootstrap", "measure", "report", "split", "run"})
STRICT_COMMANDS = frozenset({"measure", "split"})
FINAL_MONTH_COMMANDS = frozenset({"report", "consolidate"})

@dataclass(slots=True)
class Job:
    process: subprocess.Popen[str]
    command: list[str]
    output: list[str] = field(default_factory=list)
    status: str = "running"
    returncode: int | None = None

class App:
    def __init__(self, workspace: Path, pipeline_template: str) -> None:
        self.workspace = workspace.resolve(strict=True)
        self.pipeline_template = pipeline_template
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()

    def resolve_file(self, relative: str) -> Path:
        if not relative or Path(relative).suffix.lower() not in ALLOWED_SUFFIXES:
            raise ValueError("Only .yaml, .yml, and .css files are allowed")
        candidate = (self.workspace / relative).resolve()
        if not candidate.is_relative_to(self.workspace):
            raise ValueError("Path escapes the configured workspace")
        return candidate

    def files(self) -> list[str]:
        ignored = {".git", ".venv", "node_modules", "__pycache__"}
        result: list[str] = []
        for path in self.workspace.rglob("*"):
            if path.is_file() and path.suffix.lower() in ALLOWED_SUFFIXES and not any(p in ignored for p in path.parts):
                result.append(path.relative_to(self.workspace).as_posix())
        return sorted(result, key=str.casefold)

    def build_command(self, payload: dict[str, Any]) -> list[str]:
        command = str(payload.get("command", "run"))
        if command not in COMMANDS: raise ValueError("Invalid command")
        argv = shlex.split(self.pipeline_template) + [command]
        if command in NEEDS_COMPETENCE:
            competence = str(payload.get("competence", ""))
            if not COMPETENCE_RE.fullmatch(competence): raise ValueError("Invalid competence; expected YYYY-MM")
            argv.append(competence)
        if command in NEEDS_ORGAO:
            agency = str(payload.get("agency", ""))
            if agency not in AGENCIES: raise ValueError("Invalid agency")
            argv += ["--orgao", agency]
        if command in STRICT_COMMANDS and payload.get("strict"): argv.append("--strict")
        if command in FINAL_MONTH_COMMANDS and payload.get("final_month"): argv.append("--final-month")
        if command == "run":
            if payload.get("force"): argv.append("--force")
            if payload.get("clean"): argv.append("--clean")
        return argv

    def start_job(self, payload: dict[str, Any]) -> tuple[str, list[str]]:
        command = self.build_command(payload)
        process = subprocess.Popen(command, cwd=self.workspace, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, start_new_session=True)
        job_id = uuid.uuid4().hex
        job = Job(process=process, command=command)
        with self.lock: self.jobs[job_id] = job
        threading.Thread(target=self._collect, args=(job,), daemon=True).start()
        return job_id, command

    @staticmethod
    def _collect(job: Job) -> None:
        assert job.process.stdout is not None
        for line in job.process.stdout: job.output.append(line)
        job.returncode = job.process.wait()
        job.status = "succeeded" if job.returncode == 0 else "failed"

class Handler(SimpleHTTPRequestHandler):
    app: ClassVar[App]
    web_root: ClassVar[Path]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(self.web_root), **kwargs)

    def _json(self, data: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body)

    def _payload(self) -> dict[str, Any]:
        size = int(self.headers.get("Content-Length", "0"))
        if size > MAX_FILE_BYTES: raise ValueError("Request too large")
        value = json.loads(self.rfile.read(size) or b"{}")
        if not isinstance(value, dict): raise ValueError("JSON object expected")
        return value

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/api/files": return self._json({"workspace": str(self.app.workspace), "files": self.app.files()})
            if parsed.path == "/api/indicators":
                indicators = [
                    {
                        "key": d.key,
                        "name": d.name,
                        "shared_path": d.shared_rel,
                        "orgaos": list(d.orgaos),
                        "segments": [
                            {"orgao": s.orgao, "category": s.category}
                            for s in d.segments
                        ],
                    }
                    for d in inms.discover(self.app.workspace)
                ]
                return self._json({"indicators": indicators})
            if parsed.path == "/api/indicator":
                params = parse_qs(parsed.query)
                key = params.get("key", [""])[0]
                orgao = params.get("orgao", [""])[0]
                doc = inms.read_indicator(self.app.workspace, key, orgao)
                return self._json(doc)
            if parsed.path == "/api/file":
                path = self.app.resolve_file(parse_qs(parsed.query).get("path", [""])[0])
                raw = path.read_bytes()
                if len(raw) > MAX_FILE_BYTES: raise ValueError("File exceeds 2 MiB limit")
                return self._json({"content": raw.decode("utf-8")})
            if parsed.path.startswith("/api/pipeline/"):
                job_id = parsed.path.rsplit("/", 1)[-1]
                with self.app.lock: job = self.app.jobs.get(job_id)
                if job is None: return self._json({"error": "Job not found"}, HTTPStatus.NOT_FOUND)
                return self._json({"status": job.status, "returncode": job.returncode, "output": "".join(job.output)[-200_000:]})
            return super().do_GET()
        except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as exc: self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def do_PUT(self) -> None:
        try:
            path = urlparse(self.path).path
            if path == "/api/indicator":
                payload = self._payload()
                inms.save_indicator(self.app.workspace, payload)
                return self._json({"saved": True})
            if path != "/api/file": return self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            payload = self._payload(); path = self.app.resolve_file(str(payload.get("path", ""))); content = payload.get("content")
            if not isinstance(content, str): raise ValueError("content must be a string")
            encoded = content.encode("utf-8")
            if len(encoded) > MAX_FILE_BYTES: raise ValueError("File exceeds 2 MiB limit")
            if not path.is_file(): raise ValueError("File does not exist")
            backup = path.with_suffix(path.suffix + ".bak"); backup.write_bytes(path.read_bytes())
            temp = path.with_suffix(path.suffix + ".tmp"); temp.write_bytes(encoded); os.replace(temp, path)
            self._json({"saved": True, "backup": backup.relative_to(self.app.workspace).as_posix()})
        except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as exc: self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def do_POST(self) -> None:
        try:
            if urlparse(self.path).path != "/api/pipeline": return self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            job_id, command = self.app.start_job(self._payload()); self._json({"job_id": job_id, "command": shlex.join(command)}, HTTPStatus.ACCEPTED)
        except (ValueError, OSError, json.JSONDecodeError) as exc: self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def do_DELETE(self) -> None:
        try:
            job_id = urlparse(self.path).path.rsplit("/", 1)[-1]
            with self.app.lock: job = self.app.jobs.get(job_id)
            if job is None: return self._json({"error": "Job not found"}, HTTPStatus.NOT_FOUND)
            if job.process.poll() is None: job.process.terminate(); job.status = "stopping"
            self._json({"stopping": True})
        except OSError as exc: self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: Any) -> None: LOG.info(format, *args)

def main() -> int:
    parser = argparse.ArgumentParser(description="Local YAML/CSS editor and pyauditor runner")
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="Root folder exposed to the editor")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    template = os.getenv("WAYFINDER_PIPELINE_CMD", "uv run pyauditor")
    Handler.app = App(args.workspace, template); Handler.web_root = Path(__file__).resolve().parent
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    LOG.info("Serving %s with workspace %s", url, Handler.app.workspace)
    if not args.no_browser: threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try: server.serve_forever()
    except KeyboardInterrupt: LOG.info("Stopping")
    finally: server.server_close()
    return 0

if __name__ == "__main__": raise SystemExit(main())
