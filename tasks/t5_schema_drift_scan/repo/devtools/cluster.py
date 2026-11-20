"""Runs the whole system locally, one OS process per ``deploy/*.yaml`` entry.

The deploy files are the only wiring: a service reaches another service, a
database or a third-party API only through a URL declared in its
``environment``. Hosts are rewritten to local ports here, so an address that is
not declared in ``deploy/`` does not resolve.
"""
import os
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

URL = re.compile(r"^(?P<scheme>[a-z][a-z0-9+.-]*)://(?P<host>[^/:]+)(?::\d+)?(?P<rest>/.*)?$")
START_TIMEOUT_SECONDS = 20


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Cluster:
    def __init__(self, root, externals=None):
        self.root = Path(root)
        self.externals = {h: f.base_url for h, f in (externals or {}).items()}
        self.ports = {}
        self._processes = {}
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name) / "data"

    def _manifests(self):
        return [
            yaml.safe_load(path.read_text(encoding="utf-8"))
            for path in sorted((self.root / "deploy").glob("*.yaml"))
        ]

    def _init_database(self, manifest):
        directory = self.data_dir / manifest["name"]
        directory.mkdir(parents=True)
        connection = sqlite3.connect(directory / f"{manifest['database']}.sqlite3")
        schema = (self.root / manifest["schema"]).read_text(encoding="utf-8")
        connection.executescript(schema)
        connection.close()

    def _resolve(self, value):
        match = URL.match(str(value))
        if not match:
            return str(value)
        host, rest = match["host"], match["rest"] or ""
        if host in self.ports:
            return f"http://127.0.0.1:{self.ports[host]}{rest}"
        if host in self.externals:
            return f"{self.externals[host]}{rest}"
        return str(value)

    def start(self):
        manifests = self._manifests()
        services = [m for m in manifests if m["kind"] == "service"]
        for manifest in manifests:
            if manifest["kind"] == "database":
                self._init_database(manifest)
        self.ports = {m["name"]: _free_port() for m in services}

        base_env = {
            k: v
            for k, v in os.environ.items()
            if k.lower() not in {"http_proxy", "https_proxy", "all_proxy"}
        }
        logs = Path(self._tmp.name) / "logs"
        logs.mkdir()
        for manifest in services:
            env = dict(base_env)
            env.update({k: self._resolve(v) for k, v in (manifest.get("environment") or {}).items()})
            env.update(
                HOST="127.0.0.1",
                PORT=str(self.ports[manifest["name"]]),
                DATA_DIR=str(self.data_dir),
                PYTHONPATH=str(self.root),
                NO_PROXY="127.0.0.1,localhost",
            )
            log = open(logs / f"{manifest['name']}.log", "wb")
            self._processes[manifest["name"]] = (
                subprocess.Popen(
                    [sys.executable, "-m", manifest["module"]],
                    cwd=self.root,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                ),
                logs / f"{manifest['name']}.log",
            )
        for name in self._processes:
            self._wait_healthy(name)
        return self

    def _wait_healthy(self, name):
        process, log = self._processes[name]
        deadline = time.monotonic() + START_TIMEOUT_SECONDS
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break
            try:
                opener.open(f"{self.url(name)}/health", timeout=1).read()
                return
            except (urllib.error.URLError, OSError):
                time.sleep(0.05)
        raise RuntimeError(f"{name} did not start:\n{log.read_text(errors='replace')}")

    def url(self, name):
        return f"http://127.0.0.1:{self.ports[name]}"

    def stop(self):
        for process, _ in self._processes.values():
            process.terminate()
        for process, _ in self._processes.values():
            process.wait(timeout=10)
        self._tmp.cleanup()
