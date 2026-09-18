# Servidor das páginas de aplicativos

O gerenciador e as páginas são servidos exclusivamente sob `/store/`:

- Entrada do gerenciador: `https://seu-dominio/store/`
- Painel: `https://seu-dominio/store/admin/`
- Aplicativo: `https://seu-dominio/store/apps/<identificador>/`
- Guia: `https://seu-dominio/store/apps/<identificador>/ajuda/`

Não existe mais uma vitrine pública com vários aplicativos. A rota `/store/` leva ao painel, e cada aplicativo publicado é compartilhado pela sua URL direta exibida no gerenciador.

O painel não possui senha padrão. Se nenhuma credencial for configurada, a tela de login permanece bloqueada.

## Instalação

Na pasta do projeto:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

O SQLite da loja é criado automaticamente em `data/store.db`. Os uploads ficam em `media/`. Esses arquivos não são versionados pelo Git e devem entrar no backup da VPS.

## Credenciais do painel

Gere um segredo de sessão:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Gere um hash de senha sem colocar a senha no histórico do terminal:

```bash
python -c "from getpass import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass('Senha do painel: ')))"
```

Configure as variáveis no serviço, preferencialmente por um arquivo legível somente pelo usuário do processo:

```ini
STORE_SECRET_KEY=cole-o-segredo-gerado
STORE_ADMIN_PASSWORD_HASH=cole-o-hash-gerado
STORE_COOKIE_SECURE=1
STORE_MAX_UPLOAD_MB=500
```

Como alternativa temporária, `STORE_ADMIN_PASSWORD` aceita a senha em texto simples, mas o hash é preferível.

## Iniciar localmente

No Windows/PowerShell, depois de instalar as dependências:

```powershell
$env:STORE_SECRET_KEY = "segredo-local"
$env:STORE_ADMIN_PASSWORD = "senha-local"
python server.py
```

Depois abra:

```text
http://127.0.0.1:8181/store/
http://127.0.0.1:8181/store/admin/
```

## Executar na VPS

Para produção, use Gunicorn atrás do Nginx:

```bash
cd /root/PlayStore
. .venv/bin/activate
gunicorn --workers 2 --bind 127.0.0.1:8181 --access-logfile - server:app
```

As variáveis de ambiente precisam estar disponíveis para o processo do Gunicorn. Em um serviço `systemd`, use um `EnvironmentFile` fora do repositório e com permissão restrita.

## Nginx

1. Mantenha o Gunicorn ativo em `127.0.0.1:8181`.
2. Copie o conteúdo de `nginx-store.conf` para dentro do bloco `server { ... }` HTTPS já existente.
3. Valide e recarregue:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

O limite de upload do Nginx precisa ser igual ou maior que `STORE_MAX_UPLOAD_MB`.

## Backup

Faça backup conjunto de:

```text
/root/PlayStore/data/store.db
/root/PlayStore/media/
```

O banco usa o modo WAL. Para uma cópia consistente com o serviço ativo, use o comando de backup do SQLite ou pare brevemente o serviço antes de copiar os arquivos.

## Verificação rápida

```bash
curl -I http://127.0.0.1:8181/store/
curl -I http://127.0.0.1:8181/store/apps/privchat/
curl -I http://127.0.0.1:8181/store/admin/
curl http://127.0.0.1:8181/store/health
```

`/store/admin/` deve responder com redirecionamento para a tela de login quando não houver uma sessão autenticada.
