"""Reproduz a inicialização simultânea de múltiplos workers WSGI."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


with tempfile.TemporaryDirectory(prefix="personal-store-concurrent-") as test_directory:
    environment = os.environ.copy()
    environment["STORE_DATABASE"] = str(Path(test_directory) / "store.db")
    environment["STORE_SECRET_KEY"] = "segredo-do-teste-concorrente"
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", "import server"],
            cwd=Path(__file__).resolve().parents[1],
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(4)
    ]
    failures: list[str] = []
    for process in processes:
        stdout, stderr = process.communicate(timeout=30)
        if process.returncode != 0:
            failures.append(f"exit={process.returncode}\nstdout={stdout}\nstderr={stderr}")

    assert not failures, "\n\n".join(failures)

print("concurrent-boot-test-ok")
