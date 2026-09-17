#!/usr/bin/env python3
"""Servidor local do clone da Google Play sob o prefixo /store/."""

from __future__ import annotations

import argparse
import json
import os
import posixpath
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


DEFAULT_PREFIX = "/store"


class StoreRequestHandler(SimpleHTTPRequestHandler):
    """Serve apenas os arquivos do projeto expostos em /store/."""

    server_version = "PrivChatStore/1.0"

    def do_GET(self) -> None:  # noqa: N802 - nome definido pela biblioteca
        if self._redirect_or_reject():
            return
        super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802 - nome definido pela biblioteca
        if self._redirect_or_reject():
            return
        super().do_HEAD()

    def _redirect_or_reject(self) -> bool:
        request_path = urlsplit(self.path).path

        if request_path == f"{DEFAULT_PREFIX}/health":
            payload = json.dumps(
                {"status": "ok", "service": "privchat-store", "prefix": f"{DEFAULT_PREFIX}/"}
            ).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(payload)
            return True

        if request_path in ("", "/"):
            self.send_response(HTTPStatus.TEMPORARY_REDIRECT)
            self.send_header("Location", f"{DEFAULT_PREFIX}/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return True

        if request_path == DEFAULT_PREFIX:
            query = urlsplit(self.path).query
            location = f"{DEFAULT_PREFIX}/"
            if query:
                location = f"{location}?{query}"
            self.send_response(HTTPStatus.PERMANENT_REDIRECT)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return True

        if not request_path.startswith(f"{DEFAULT_PREFIX}/"):
            self.send_error(HTTPStatus.NOT_FOUND, "Rota não encontrada")
            return True

        return False

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        if code != HTTPStatus.NOT_FOUND:
            super().send_error(code, message, explain)
            return

        error_page = Path(self.directory) / "404.html"
        if not error_page.is_file():
            super().send_error(code, message, explain)
            return

        payload = error_page.read_bytes()
        self.send_response(HTTPStatus.NOT_FOUND)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def translate_path(self, path: str) -> str:
        """Remove /store com segurança antes de resolver o arquivo local."""
        request_path = unquote(urlsplit(path).path)
        relative_path = request_path[len(DEFAULT_PREFIX) :]
        normalized = posixpath.normpath(relative_path)
        parts = [part for part in normalized.split("/") if part not in ("", ".", "..")]

        resolved = Path(self.directory)
        for part in parts:
            if os.path.dirname(part):
                continue
            resolved /= part
        return str(resolved)

    def guess_type(self, path: str) -> str:
        if path.lower().endswith(".apk"):
            return "application/vnd.android.package-archive"
        return super().guess_type(path)

    def end_headers(self) -> None:
        request_path = urlsplit(self.path).path.lower()
        if request_path.endswith(".apk"):
            self.send_header("Content-Disposition", 'attachment; filename="PrivChat.apk"')
            self.send_header("X-Content-Type-Options", "nosniff")
        elif request_path.endswith((".html", "/")):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve o clone local em /store/.")
    parser.add_argument("--host", default="127.0.0.1", help="Endereço de escuta (padrão: 127.0.0.1)")
    parser.add_argument("--port", default=8181, type=int, help="Porta HTTP (padrão: 8181)")
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Pasta contendo os arquivos do clone",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    directory = args.directory.resolve()
    handler = partial(StoreRequestHandler, directory=str(directory))

    with ThreadingHTTPServer((args.host, args.port), handler) as httpd:
        print(f"Loja disponível em http://{args.host}:{args.port}{DEFAULT_PREFIX}/")
        print(f"Servindo arquivos de {directory}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor encerrado.")


if __name__ == "__main__":
    main()
