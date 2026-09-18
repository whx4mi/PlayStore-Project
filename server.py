#!/usr/bin/env python3
"""Loja pessoal de aplicativos publicada integralmente sob /store/."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import uuid
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Iterator, TypeVar

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MEDIA_DIR = BASE_DIR / "media"
DATABASE_PATH = Path(os.environ.get("STORE_DATABASE", DATA_DIR / "store.db"))
DEFAULT_PREFIX = "/store"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
APK_EXTENSIONS = {".apk"}

app = Flask(__name__, template_folder=str(BASE_DIR), static_folder=None)
app.config.update(
    SECRET_KEY=os.environ.get("STORE_SECRET_KEY") or secrets.token_hex(32),
    MAX_CONTENT_LENGTH=int(os.environ.get("STORE_MAX_UPLOAD_MB", "500")) * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("STORE_COOKIE_SECURE", "0") == "1",
)

F = TypeVar("F", bound=Callable[..., Any])


@contextmanager
def database() -> Iterator[sqlite3.Connection]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 10000")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_database() -> None:
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    with database() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS apps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                developer TEXT NOT NULL,
                purchase_info TEXT NOT NULL DEFAULT '',
                short_description TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT 'Apps',
                tags TEXT NOT NULL DEFAULT '',
                rating REAL NOT NULL DEFAULT 5.0 CHECK (rating >= 0 AND rating <= 5),
                rating_count_label TEXT NOT NULL DEFAULT 'Sem avaliações',
                downloads_label TEXT NOT NULL DEFAULT 'Novo',
                age_rating TEXT NOT NULL DEFAULT 'L',
                version_name TEXT NOT NULL DEFAULT '1.0.0',
                minimum_android TEXT NOT NULL DEFAULT '8.0',
                updated_at_label TEXT NOT NULL DEFAULT '',
                icon_path TEXT NOT NULL DEFAULT 'fallback-app.svg',
                banner_path TEXT,
                apk_path TEXT,
                download_filename TEXT NOT NULL DEFAULT 'aplicativo.apk',
                showcase_title TEXT NOT NULL DEFAULT '',
                safety_text TEXT NOT NULL DEFAULT 'Verifique as permissões solicitadas antes de instalar.',
                published INTEGER NOT NULL DEFAULT 0,
                featured INTEGER NOT NULL DEFAULT 0,
                priority INTEGER NOT NULL DEFAULT 100,
                real_app INTEGER NOT NULL DEFAULT 1,
                download_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id INTEGER NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
                author_name TEXT NOT NULL,
                rating INTEGER NOT NULL DEFAULT 5 CHECK (rating >= 1 AND rating <= 5),
                review_date TEXT NOT NULL,
                body TEXT NOT NULL,
                display_order INTEGER NOT NULL DEFAULT 100,
                published INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS download_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id INTEGER NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
                downloaded_at TEXT NOT NULL,
                ip_hash TEXT,
                user_agent TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_apps_public
                ON apps(published, real_app, featured, priority, created_at);
            CREATE INDEX IF NOT EXISTS idx_reviews_app
                ON reviews(app_id, published, display_order);
            """
        )
        count = connection.execute("SELECT COUNT(*) FROM apps").fetchone()[0]
        if count == 0:
            seed_privchat(connection)


def seed_privchat(connection: sqlite3.Connection) -> None:
    now = datetime.now(timezone.utc).isoformat()
    cursor = connection.execute(
        """
        INSERT INTO apps (
            slug, name, developer, purchase_info, short_description, description,
            category, tags, rating, rating_count_label, downloads_label,
            age_rating, version_name, minimum_android, updated_at_label,
            icon_path, apk_path, download_filename, showcase_title, safety_text,
            published, featured, priority, real_app, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, 1, 1, ?, ?)
        """,
        (
            "privchat",
            "PrivChat",
            "PrivChat Technologies",
            "Contém anúncios · Compras no app",
            "Mensagens rápidas, grupos, fotos, áudios e chamadas em uma experiência simples, leve e segura.",
            "PrivChat deixa suas conversas mais leves e privadas. Envie mensagens, fotos e áudios, organize grupos e mantenha contato com quem importa em uma interface rápida e fácil de usar. Seus bate-papos ficam organizados e acessíveis em todos os momentos.",
            "Comunicação · Privacidade",
            "Comunicação,Mensagens,Privacidade,Chamadas",
            4.7,
            "28,4 mil avaliações",
            "200 mil+",
            "L",
            "2.4.7",
            "8.0",
            "14 de setembro de 2026",
            "privchat-v2.png",
            "app.apk",
            "PrivChat.apk",
            "Converse com liberdade e privacidade",
            "Os dados são criptografados em trânsito|Você pode solicitar a exclusão dos dados",
            now,
            now,
        ),
    )
    app_id = cursor.lastrowid
    connection.executemany(
        """
        INSERT INTO reviews (app_id, author_name, rating, review_date, body, display_order)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (app_id, "Mariana Souza", 5, "12 de setembro de 2026", "Finalmente um app de mensagens leve e fácil de usar. As conversas abrem rápido e o visual é muito limpo.", 1),
            (app_id, "Lucas Martins", 5, "8 de setembro de 2026", "Uso todos os dias com minha família. As notificações chegam certinho e gostei muito do foco em privacidade.", 2),
            (app_id, "Camila Ribeiro", 5, "2 de setembro de 2026", "Interface simples, bonita e sem complicação. Migrei meus grupos para o PrivChat e estou adorando.", 3),
        ],
    )


def row_to_app(row: sqlite3.Row, reviews: list[sqlite3.Row] | None = None) -> dict[str, Any]:
    result = dict(row)
    result["tags_list"] = [tag.strip() for tag in result.get("tags", "").split(",") if tag.strip()]
    result["safety_items"] = [item.strip() for item in result.get("safety_text", "").split("|") if item.strip()]
    result["rating_display"] = f"{float(result['rating']):.1f}".replace(".", ",")
    result["reviews"] = [dict(review) for review in (reviews or [])]
    return result


def get_app(slug: str, include_drafts: bool = False) -> dict[str, Any] | None:
    with database() as connection:
        query = "SELECT * FROM apps WHERE slug = ?"
        if not include_drafts:
            query += " AND published = 1"
        row = connection.execute(query, (slug,)).fetchone()
        if row is None:
            return None
        reviews = connection.execute(
            "SELECT * FROM reviews WHERE app_id = ? AND published = 1 ORDER BY display_order, id",
            (row["id"],),
        ).fetchall()
        return row_to_app(row, reviews)


def public_apps() -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            """
            SELECT * FROM apps
            WHERE published = 1 AND real_app = 1
            ORDER BY featured DESC, priority ASC, created_at DESC
            """
        ).fetchall()
        return [row_to_app(row) for row in rows]


def admin_configured() -> bool:
    return bool(os.environ.get("STORE_ADMIN_PASSWORD_HASH") or os.environ.get("STORE_ADMIN_PASSWORD"))


def password_matches(value: str) -> bool:
    password_hash = os.environ.get("STORE_ADMIN_PASSWORD_HASH")
    if password_hash:
        return check_password_hash(password_hash, value)
    password = os.environ.get("STORE_ADMIN_PASSWORD")
    return bool(password) and hmac.compare_digest(password, value)


def csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def verify_csrf() -> None:
    expected = session.get("csrf_token", "")
    supplied = request.form.get("csrf_token", "")
    if not expected or not hmac.compare_digest(expected, supplied):
        abort(400, "Token CSRF inválido")


def admin_required(function: F) -> F:
    @wraps(function)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if not session.get("store_admin"):
            return redirect(url_for("admin_login", next=request.path))
        return function(*args, **kwargs)

    return wrapped  # type: ignore[return-value]


def form_text(name: str, default: str = "") -> str:
    return request.form.get(name, default).strip()


def form_int(name: str, default: int = 0) -> int:
    try:
        return int(request.form.get(name, str(default)))
    except ValueError:
        return default


def form_float(name: str, default: float = 0.0) -> float:
    raw = request.form.get(name, str(default)).replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return default


def image_signature_valid(path: Path) -> bool:
    header = path.read_bytes()[:16]
    return (
        header.startswith(b"\x89PNG\r\n\x1a\n")
        or header.startswith(b"\xff\xd8\xff")
        or (len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP")
    )


def save_upload(field: str, slug: str, allowed: set[str], kind: str) -> str | None:
    upload = request.files.get(field)
    if upload is None or not upload.filename:
        return None
    extension = Path(upload.filename).suffix.lower()
    if extension not in allowed:
        raise ValueError(f"Formato inválido para {kind}.")
    target_dir = MEDIA_DIR / slug
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{kind}-{uuid.uuid4().hex[:12]}{extension}"
    target = target_dir / filename
    upload.save(target)
    valid = image_signature_valid(target) if allowed == IMAGE_EXTENSIONS else zipfile.is_zipfile(target)
    if not valid:
        target.unlink(missing_ok=True)
        raise ValueError(f"O arquivo enviado como {kind} não passou na validação.")
    return target.relative_to(BASE_DIR).as_posix()


def app_payload(existing: sqlite3.Row | None = None) -> dict[str, Any]:
    existing_data = dict(existing) if existing else {}
    slug = form_text("slug").lower()
    if not SLUG_RE.fullmatch(slug):
        raise ValueError("O identificador deve usar somente letras minúsculas, números e hífens.")
    name = form_text("name")
    developer = form_text("developer")
    if not name or not developer:
        raise ValueError("Nome e desenvolvedor são obrigatórios.")

    icon_path = save_upload("icon", slug, IMAGE_EXTENSIONS, "icon") or existing_data.get("icon_path") or "fallback-app.svg"
    banner_path = save_upload("banner", slug, IMAGE_EXTENSIONS, "banner") or existing_data.get("banner_path")
    apk_path = save_upload("apk", slug, APK_EXTENSIONS, "app") or existing_data.get("apk_path")
    rating = max(0.0, min(5.0, form_float("rating", 5.0)))
    download_filename = form_text("download_filename", f"{name}.apk")
    if not download_filename.lower().endswith(".apk"):
        download_filename += ".apk"

    return {
        "slug": slug,
        "name": name,
        "developer": developer,
        "purchase_info": form_text("purchase_info"),
        "short_description": form_text("short_description"),
        "description": form_text("description"),
        "category": form_text("category", "Apps"),
        "tags": form_text("tags"),
        "rating": rating,
        "rating_count_label": form_text("rating_count_label", "Sem avaliações"),
        "downloads_label": form_text("downloads_label", "Novo"),
        "age_rating": form_text("age_rating", "L"),
        "version_name": form_text("version_name", "1.0.0"),
        "minimum_android": form_text("minimum_android", "8.0"),
        "updated_at_label": form_text("updated_at_label"),
        "icon_path": icon_path,
        "banner_path": banner_path,
        "apk_path": apk_path,
        "download_filename": download_filename,
        "showcase_title": form_text("showcase_title", name),
        "safety_text": form_text("safety_text", "Verifique as permissões solicitadas antes de instalar."),
        "published": 1 if request.form.get("published") == "1" else 0,
        "featured": 1 if request.form.get("featured") == "1" else 0,
        "priority": max(0, form_int("priority", 100)),
    }


@app.context_processor
def inject_helpers() -> dict[str, Any]:
    return {"csrf_token": csrf_token}


@app.after_request
def security_headers(response: Any) -> Any:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    if request.path.startswith(f"{DEFAULT_PREFIX}/admin"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Frame-Options"] = "DENY"
    elif request.path.endswith(".html") or request.path.endswith("/"):
        response.headers.setdefault("Cache-Control", "no-cache")
    return response


@app.route("/")
def root_redirect() -> Any:
    return redirect(f"{DEFAULT_PREFIX}/", code=307)


@app.route(DEFAULT_PREFIX)
def store_redirect() -> Any:
    return redirect(f"{DEFAULT_PREFIX}/", code=308)


@app.route(f"{DEFAULT_PREFIX}/")
@app.route(f"{DEFAULT_PREFIX}/index.html")
def store_home() -> Any:
    real_apps = public_apps()
    featured_app = next((item for item in real_apps if item["featured"]), real_apps[0] if real_apps else None)
    return render_template("index.html", real_apps=real_apps, featured_app=featured_app)


@app.route(f"{DEFAULT_PREFIX}/apps/<slug>/")
def app_detail(slug: str) -> Any:
    selected = get_app(slug)
    if selected is None:
        return render_template("404.html"), 404
    return render_template("privchat.html", app=selected, asset_base="../../")


@app.route(f"{DEFAULT_PREFIX}/privchat.html")
def legacy_privchat() -> Any:
    selected = get_app("privchat")
    if selected is None:
        return render_template("404.html"), 404
    return render_template("privchat.html", app=selected, asset_base="./")


@app.route(f"{DEFAULT_PREFIX}/download/<slug>/")
def download_app(slug: str) -> Any:
    selected = get_app(slug)
    if selected is None or not selected.get("apk_path"):
        abort(404)
    apk_path = (BASE_DIR / selected["apk_path"]).resolve()
    if BASE_DIR not in apk_path.parents or not apk_path.is_file():
        abort(404)
    if request.method != "HEAD":
        now = datetime.now(timezone.utc).isoformat()
        remote = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
        ip_hash = hashlib.sha256(f"{selected['id']}:{remote}".encode()).hexdigest()[:24] if remote else None
        with database() as connection:
            connection.execute("UPDATE apps SET download_count = download_count + 1 WHERE id = ?", (selected["id"],))
            connection.execute(
                "INSERT INTO download_events (app_id, downloaded_at, ip_hash, user_agent) VALUES (?, ?, ?, ?)",
                (selected["id"], now, ip_hash, request.user_agent.string[:300]),
            )
    return send_file(
        apk_path,
        as_attachment=True,
        download_name=selected["download_filename"],
        mimetype="application/vnd.android.package-archive",
        conditional=True,
    )


@app.route(f"{DEFAULT_PREFIX}/health")
def health() -> Any:
    return {"status": "ok", "service": "personal-app-store", "prefix": f"{DEFAULT_PREFIX}/"}


@app.route(f"{DEFAULT_PREFIX}/admin/login", methods=["GET", "POST"])
def admin_login() -> Any:
    if request.method == "POST":
        verify_csrf()
        if not admin_configured():
            flash("Configure STORE_ADMIN_PASSWORD ou STORE_ADMIN_PASSWORD_HASH antes de usar o painel.", "error")
        elif password_matches(request.form.get("password", "")):
            session.clear()
            session["store_admin"] = True
            csrf_token()
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Senha inválida.", "error")
    return render_template("admin.html", mode="login", configured=admin_configured())


@app.post(f"{DEFAULT_PREFIX}/admin/logout")
@admin_required
def admin_logout() -> Any:
    verify_csrf()
    session.clear()
    return redirect(url_for("admin_login"))


@app.route(f"{DEFAULT_PREFIX}/admin/")
@admin_required
def admin_dashboard() -> Any:
    with database() as connection:
        rows = connection.execute(
            "SELECT * FROM apps ORDER BY published DESC, priority ASC, created_at DESC"
        ).fetchall()
    return render_template("admin.html", mode="list", apps=[dict(item) for item in rows])


@app.route(f"{DEFAULT_PREFIX}/admin/apps/new", methods=["GET", "POST"])
@admin_required
def admin_app_new() -> Any:
    if request.method == "POST":
        verify_csrf()
        try:
            payload = app_payload()
            now = datetime.now(timezone.utc).isoformat()
            columns = ", ".join(payload.keys())
            placeholders = ", ".join("?" for _ in payload)
            with database() as connection:
                connection.execute(
                    f"INSERT INTO apps ({columns}, real_app, created_at, updated_at) VALUES ({placeholders}, 1, ?, ?)",
                    (*payload.values(), now, now),
                )
            flash("Aplicativo criado com sucesso.", "success")
            return redirect(url_for("admin_dashboard"))
        except (ValueError, sqlite3.IntegrityError) as error:
            flash(str(error), "error")
    return render_template("admin.html", mode="form", item=None, reviews=[])


@app.route(f"{DEFAULT_PREFIX}/admin/apps/<int:app_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_app_edit(app_id: int) -> Any:
    with database() as connection:
        existing = connection.execute("SELECT * FROM apps WHERE id = ?", (app_id,)).fetchone()
    if existing is None:
        abort(404)
    if request.method == "POST":
        verify_csrf()
        try:
            payload = app_payload(existing)
            assignments = ", ".join(f"{column} = ?" for column in payload)
            with database() as connection:
                connection.execute(
                    f"UPDATE apps SET {assignments}, updated_at = ? WHERE id = ?",
                    (*payload.values(), datetime.now(timezone.utc).isoformat(), app_id),
                )
            flash("Aplicativo atualizado.", "success")
            return redirect(url_for("admin_app_edit", app_id=app_id))
        except (ValueError, sqlite3.IntegrityError) as error:
            flash(str(error), "error")
    with database() as connection:
        refreshed = connection.execute("SELECT * FROM apps WHERE id = ?", (app_id,)).fetchone()
        reviews = connection.execute(
            "SELECT * FROM reviews WHERE app_id = ? ORDER BY display_order, id", (app_id,)
        ).fetchall()
    return render_template(
        "admin.html", mode="form", item=dict(refreshed), reviews=[dict(review) for review in reviews]
    )


@app.post(f"{DEFAULT_PREFIX}/admin/apps/<int:app_id>/reviews")
@admin_required
def admin_review_new(app_id: int) -> Any:
    verify_csrf()
    author = form_text("author_name")
    body = form_text("body")
    if not author or not body:
        flash("Autor e comentário são obrigatórios.", "error")
        return redirect(url_for("admin_app_edit", app_id=app_id))
    with database() as connection:
        exists = connection.execute("SELECT 1 FROM apps WHERE id = ?", (app_id,)).fetchone()
        if exists is None:
            abort(404)
        connection.execute(
            """
            INSERT INTO reviews (app_id, author_name, rating, review_date, body, display_order, published)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (
                app_id,
                author,
                max(1, min(5, form_int("rating", 5))),
                form_text("review_date", datetime.now().strftime("%d/%m/%Y")),
                body,
                max(0, form_int("display_order", 100)),
            ),
        )
    flash("Comentário adicionado.", "success")
    return redirect(url_for("admin_app_edit", app_id=app_id))


@app.post(f"{DEFAULT_PREFIX}/admin/reviews/<int:review_id>/delete")
@admin_required
def admin_review_delete(review_id: int) -> Any:
    verify_csrf()
    with database() as connection:
        review = connection.execute("SELECT app_id FROM reviews WHERE id = ?", (review_id,)).fetchone()
        if review is None:
            abort(404)
        connection.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
    flash("Comentário removido.", "success")
    return redirect(url_for("admin_app_edit", app_id=review["app_id"]))


@app.route(f"{DEFAULT_PREFIX}/<path:filename>")
def store_file(filename: str) -> Any:
    path = Path(filename)
    blocked_names = {"admin.html", "server.py", "store.db", "requirements.txt", "CONTEXTO-PROJETO.md"}
    blocked_prefixes = ("data/", "tests/", ".git/", ".codex/", ".agents/", "__pycache__/")
    allowed_extensions = {".html", ".js", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".apk", ".ico"}
    if path.name in blocked_names or filename.startswith(blocked_prefixes) or path.suffix.lower() not in allowed_extensions:
        abort(404)
    target = (BASE_DIR / filename).resolve()
    if BASE_DIR not in target.parents or not target.is_file():
        return render_template("404.html"), 404
    if target.suffix.lower() == ".apk":
        return send_file(
            target,
            as_attachment=True,
            download_name="PrivChat.apk" if target.name == "app.apk" else target.name,
            mimetype="application/vnd.android.package-archive",
            conditional=True,
        )
    return send_from_directory(BASE_DIR, filename)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve a loja pessoal em /store/.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8181, type=int)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


init_database()


if __name__ == "__main__":
    args = parse_args()
    print(f"Loja disponível em http://{args.host}:{args.port}{DEFAULT_PREFIX}/")
    print(f"Painel em http://{args.host}:{args.port}{DEFAULT_PREFIX}/admin/")
    if not admin_configured():
        print("AVISO: painel bloqueado até STORE_ADMIN_PASSWORD ou STORE_ADMIN_PASSWORD_HASH ser configurado.")
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
