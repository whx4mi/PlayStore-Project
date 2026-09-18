"""Verificação rápida das rotas essenciais, sem iniciar um servidor HTTP."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

test_directory = tempfile.TemporaryDirectory(prefix="personal-store-test-")
os.environ["STORE_DATABASE"] = str(Path(test_directory.name) / "store.db")
os.environ["STORE_ADMIN_PASSWORD"] = "teste-local"
os.environ["STORE_SECRET_KEY"] = "segredo-de-teste-local"

from server import app  # noqa: E402 - ambiente precisa ser definido antes da importação


client = app.test_client()
paths = [
    "/",
    "/store",
    "/store/",
    "/store/index.html",
    "/store/privchat.html",
    "/store/ajuda-instalacao.html",
    "/store/apps/privchat/",
    "/store/apps/privchat/ajuda/",
    "/store/category.html?tab=apps",
    "/store/health",
    "/store/admin/",
    "/store/admin/login",
]

results = [(path, client.get(path, follow_redirects=False).status_code) for path in paths]
print(results)

login_page = client.get("/store/admin/login")
match = re.search(rb'name="csrf_token" value="([^"]+)', login_page.data)
assert match, "Token CSRF não encontrado"
response = client.post(
    "/store/admin/login",
    data={"csrf_token": match.group(1).decode(), "password": "teste-local"},
    follow_redirects=True,
)
assert response.status_code == 200
assert b"Aplicativos" in response.data
assert client.head("/store/download/privchat/").status_code == 200
assert client.get("/store/server.py").status_code == 404
assert client.get("/store/tests/smoke_test.py").status_code == 404

with client.session_transaction() as current_session:
    token = current_session["csrf_token"]

created = client.post(
    "/store/admin/apps/new",
    data={
        "csrf_token": token,
        "name": "Aplicativo de Teste",
        "slug": "aplicativo-teste",
        "developer": "Desenvolvedor Local",
        "category": "Ferramentas",
        "short_description": "Descrição curta para o teste.",
        "description": "Descrição completa para o teste automatizado.",
        "rating": "4,8",
        "rating_5_pct": "70",
        "rating_4_pct": "20",
        "rating_3_pct": "7",
        "rating_2_pct": "2",
        "rating_1_pct": "1",
        "rating_count_label": "120 avaliações",
        "downloads_label": "500+",
        "published": "1",
        "featured": "1",
        "priority": "0",
    },
    follow_redirects=True,
)
assert created.status_code == 200
assert b"Aplicativo criado com sucesso" in created.data
detail = client.get("/store/apps/aplicativo-teste/")
assert detail.status_code == 200
assert b"Aplicativo de Teste" in detail.data
assert b"width:70.0%" in detail.data
assert b'href="./ajuda/"' in detail.data
assert b"{%" not in detail.data and b"{{" not in detail.data
help_page = client.get("/store/apps/aplicativo-teste/ajuda/")
assert help_page.status_code == 200
assert b"Ajuda para instalar o Aplicativo de Teste" in help_page.data
assert b"Aplicativo de Teste.apk" in help_page.data
assert b"desative o Google Play Protect" in help_page.data
assert b"{%" not in help_page.data and b"{{" not in help_page.data
home = client.get("/store/")
assert home.status_code == 200
assert home.data.index(b"Aplicativo de Teste") < home.data.index(b"Balatro")
assert b"{%" not in home.data and b"{{" not in home.data

invalid_distribution = client.post(
    "/store/admin/apps/new",
    data={
        "csrf_token": token,
        "name": "Distribuição Inválida",
        "slug": "distribuicao-invalida",
        "developer": "Teste",
        "rating_5_pct": "50",
        "rating_4_pct": "20",
        "rating_3_pct": "10",
        "rating_2_pct": "10",
        "rating_1_pct": "5",
    },
    follow_redirects=True,
)
assert b"deve totalizar 100%" in invalid_distribution.data
assert client.get("/store/apps/distribuicao-invalida/").status_code == 404
print("smoke-test-ok")
