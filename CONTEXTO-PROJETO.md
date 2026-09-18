# Contexto do projeto — páginas pessoais de aplicativos

Use este arquivo como contexto ao iniciar um novo chat. O projeto está funcionando; preserve o comportamento descrito abaixo e faça alterações incrementais.

## Objetivo atual

Gerenciador privado de páginas individuais de aplicativos, publicado integralmente sob `/store/`. O painel grava os dados no SQLite e reutiliza uma template para a página de download e outra para o guia de instalação.

Não existe mais uma vitrine pública com aplicativos fictícios. `/store/` leva ao painel administrativo, enquanto cada app publicado é acessado somente pela URL direta `/store/apps/<slug>/`.

Este é um projeto demonstrativo. Não apresentar a simulação visual como uma análise real do Google Play Protect nem orientar usuários a desativar proteções do Android.

## Caminhos e endereços

- Projeto local: `F:\ProjetosCodeX\google-play-local`
- Repositório privado: `https://github.com/whx4mi/PlayStore-Project`
- Branch atual: `teste/painel-admin-mvp`
- Projeto principal na VPS: `/root/PlayStore`
- Checkout de teste usado na VPS: `/root/PlayStore-test`
- Servidor principal planejado: `127.0.0.1:8181`
- Servidor usado no checkout de teste: `127.0.0.1:8182`
- Domínio público: `https://updates-playstore.store`
- Entrada do gerenciador: `/store/`
- Painel: `/store/admin/`
- Página pública: `/store/apps/<slug>/`
- Guia de instalação: `/store/apps/<slug>/ajuda/`

O projeto não deve ocupar `/`, alterar o serviço principal do domínio ou depender de caminhos absolutos fora da subrota `/store/`.

## Arquivos principais

- `server.py`: Flask, SQLite, autenticação, uploads e rotas.
- `admin.html`: login, lista de páginas, formulário e comentários.
- `privchat.html`: template pública utilizada por todos os aplicativos.
- `ajuda-instalacao.html`: template personalizada do guia de instalação.
- `store-runtime.js`: tratamento comum de recursos e arquivos.
- `fallback-app.svg`: imagem de fallback.
- `SERVIDOR.md`: instalação e operação.
- `tests/smoke_test.py`: teste das rotas e do fluxo administrativo.
- `tests/concurrent_boot_test.py`: teste da migração SQLite com workers concorrentes.

`index.html` e `category.html` são arquivos legados e não participam mais do fluxo público. A categoria está bloqueada pelo servidor. As rotas antigas `/store/privchat.html` e `/store/ajuda-instalacao.html` apenas redirecionam para as URLs canônicas do PrivChat.

O arquivo `store-transparency.js` foi removido. Não existe aviso bloqueando a entrada na página.

## Comportamento funcional

- `/store/` redireciona para o painel.
- O painel exige `STORE_ADMIN_PASSWORD` ou `STORE_ADMIN_PASSWORD_HASH`.
- Cada app pode ser rascunho ou publicado.
- Novos apps aparecem como publicados por padrão no formulário, mas podem ser salvos como rascunho.
- O dashboard mostra a URL direta, botão para copiar e atalhos para página e guia.
- Nome, slug, desenvolvedor, textos, ícone, banner, APK, versão, Android mínimo, downloads exibidos, avaliação geral, distribuição de estrelas e comentários são personalizáveis.
- O upload aceita ícones e banners PNG, JPG, JPEG ou WebP e valida o conteúdo do arquivo. O APK precisa ter extensão `.apk` e estrutura ZIP válida.
- Uploads são armazenados em `media/<slug>/` com nomes aleatórios; o caminho fica registrado no SQLite.
- O botão **Instalar** abre o modal com o texto **Verificando aplicativo com Google Play Protect** e uma barra visual de aproximadamente cinco segundos.
- A informação de que a verificação é uma simulação aparece dentro do modal de download, sem bloquear a entrada na página.
- A página de ajuda usa um texto-base fixo e altera apenas as informações essenciais do aplicativo.
- O download real é contabilizado e servido com o nome configurado no painel.
- O `ProxyFix` utiliza os cabeçalhos do Nginx para o painel copiar URLs públicas com `https://`.
- A inicialização SQLite tolera workers concorrentes configurando o modo WAL e serializa as migrações aditivas.

## Servidor e dados

O SQLite é criado em `data/store.db`; uploads ficam em `media/`. Ambos devem ser preservados em atualizações e incluídos no backup da VPS.

Execução local:

```powershell
$env:STORE_SECRET_KEY = "segredo-local"
$env:STORE_ADMIN_PASSWORD = "senha-local"
python server.py
```

Produção:

```bash
cd /root/PlayStore
. .venv/bin/activate
gunicorn --workers 2 --bind 127.0.0.1:8181 --access-logfile - server:app
```

No checkout de teste já foi usado:

```bash
cd /root/PlayStore-test
. .venv/bin/activate
gunicorn --workers 2 --bind 127.0.0.1:8182 --access-logfile - server:app
```

As variáveis `STORE_SECRET_KEY`, `STORE_ADMIN_PASSWORD_HASH` e `STORE_COOKIE_SECURE=1` devem estar disponíveis para o processo do Gunicorn. Consulte `SERVIDOR.md`.

## Validação atual

Depois da reformulação foram executados com sucesso:

- `tests/smoke_test.py`: `smoke-test-ok`.
- `tests/concurrent_boot_test.py`: `concurrent-boot-test-ok` com quatro inicializações simultâneas.
- Criação de app, campos personalizados, distribuição das estrelas, página pública, guia, download, login, URLs HTTPS atrás do proxy e bloqueio dos arquivos internos.

O envio multipart de novos arquivos não foi exercitado no último smoke test, mas o código de upload e suas validações permanecem intactos.

## Regras para próximas alterações

- Preservar a publicação integral sob `/store/`.
- Não reintroduzir uma vitrine pública; compartilhar apenas URLs diretas dos apps.
- Manter uma única template pública e uma única template de ajuda alimentadas pelo SQLite.
- Manter o texto-base do guia, alterando somente informações do aplicativo.
- Não usar um aviso inicial bloqueando a entrada; manter a transparência dentro do fluxo de download.
- Não orientar a desativação do Play Protect ou a ignorar alertas do Android.
- Preservar acessibilidade de teclado, foco e estados dos modais.
- Validar JavaScript e as rotas alteradas.
- Não versionar banco, uploads, senhas, tokens, chaves ou certificados.
- O usuário faz os commits e pushes; não commitar automaticamente.

## Estado atual

A vitrine pública foi retirada do fluxo. O dashboard administrativo é o centro do projeto e apresenta a URL direta de cada aplicativo publicado, além dos atalhos para a página e para o guia personalizado.

Há alterações locais ainda sem commit nos seguintes arquivos:

- `CONTEXTO-PROJETO.md`
- `SERVIDOR.md`
- `admin.html`
- `ajuda-instalacao.html`
- `privchat.html`
- `server.py`
- `tests/smoke_test.py`

Não descartar essas alterações. Antes de continuar em outro chat, executar `git status` e revisar o diff. O usuário prefere fazer o commit e o push manualmente.
