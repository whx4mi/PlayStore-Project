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
    "/store/apps/privchat/",
    "/store/apps/privchat/ajuda/",
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
assert b"Cada item publicado possui uma p\xc3\xa1gina de download" in response.data
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
assert b"Verificando aplicativo com Google Play Protect" in detail.data
assert b"Esta verifica\xc3\xa7\xc3\xa3o \xc3\xa9 uma simula\xc3\xa7\xc3\xa3o visual" in detail.data
assert b"{%" not in detail.data and b"{{" not in detail.data
help_page = client.get("/store/apps/aplicativo-teste/ajuda/")
assert help_page.status_code == 200
assert b"Ajuda para instalar o Aplicativo de Teste" in help_page.data
assert b"Aplicativo de Teste.apk" in help_page.data
assert b"Mantenha o Google Play Protect ativo" in help_page.data
assert b"Desabilite" not in help_page.data
assert b"{%" not in help_page.data and b"{{" not in help_page.data
help_text = help_page.get_data(as_text=True)
fixed_help_phrases = [
    "Encontre abaixo o sintoma que você está vendo e siga as etapas. Comece sempre confirmando que o download foi concluído.",
    "Uma interrupção de rede pode deixar o arquivo incompleto. Exclua somente o download incompleto, confira a conexão e faça um novo download pela página do Aplicativo de Teste.",
    "Libere espaço no dispositivo removendo apenas arquivos e aplicativos que você não precisa. Depois, reinicie o download.",
    "Esta demonstração informa compatibilidade com Android 8.0 ou superior. Confira a versão do Android nas configurações do aparelho e mantenha o sistema atualizado.",
    "Versões assinadas por desenvolvedores diferentes podem entrar em conflito. Faça backup dos dados importantes e procure uma versão compatível fornecida pela mesma origem da instalação existente.",
    "Reinicie o dispositivo e tente novamente. Se o Android identificar o arquivo como perigoso, interrompa a instalação.",
]
assert all(phrase in help_text for phrase in fixed_help_phrases)
home = client.get("/store/")
assert home.status_code == 200
assert home.data.index(b"Aplicativo de Teste") < home.data.index(b"Balatro")
assert b'href="./apps/aplicativo-teste/"' not in home.data
assert b'data-target="./apps/aplicativo-teste/"' in home.data
assert b"{%" not in home.data and b"{{" not in home.data
assert client.get("/store/index.html").status_code == 200
assert client.get("/store/category.html?tab=apps").status_code == 404
legacy_detail = client.get("/store/privchat.html")
assert legacy_detail.status_code == 308
assert legacy_detail.headers["Location"].endswith("/store/apps/privchat/")
legacy_help = client.get("/store/ajuda-instalacao.html")
assert legacy_help.status_code == 308
assert legacy_help.headers["Location"].endswith("/store/apps/privchat/ajuda/")

dashboard = client.get("/store/admin/")
assert dashboard.status_code == 200
assert b"/store/apps/aplicativo-teste/" in dashboard.data
assert b"Copiar URL" in dashboard.data
assert b"Abrir guia" in dashboard.data
proxied_dashboard = client.get(
    "/store/admin/",
    headers={"X-Forwarded-Proto": "https", "X-Forwarded-Host": "apps.exemplo.test"},
)
assert b"https://apps.exemplo.test/store/apps/aplicativo-teste/" in proxied_dashboard.data

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
