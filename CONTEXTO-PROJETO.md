# Contexto do projeto — Google Play local / PrivChat

Use este arquivo como contexto ao iniciar um novo chat. O projeto está funcionando; preserve o comportamento descrito abaixo e faça alterações incrementais.

## Objetivo

Clone visual da área brasileira da Google Play para portfólio, executado localmente e publicado sob a subrota `/store/` de um domínio que já possui outra plataforma na rota principal.

O clone não deve ocupar `/`, alterar o serviço principal do domínio ou depender de caminhos absolutos. Todos os links e recursos internos devem continuar funcionando quando acessados por `/store/`.

Este é um projeto demonstrativo. Não apresentar a simulação visual como uma análise real do Google Play Protect nem orientar usuários a desativar proteções do Android.

## Caminhos e endereços

- Projeto local: `F:\ProjetosCodeX\google-play-local`
- Repositório privado: `https://github.com/whx4mi/PlayStore-Project`
- Projeto na VPS: `/root/PlayStore`
- Servidor Python: `127.0.0.1:8181`
- URL local: `http://127.0.0.1:8181/store/`
- URL pública: `https://updates-playstore.store/store/`
- Página do aplicativo: `/store/privchat.html`
- Página de ajuda: `/store/ajuda-instalacao.html`

## Arquivos principais

- `index.html`: página inicial da loja.
- `category.html`: conteúdo das abas Jogos, Apps, Filmes e TV, Livros e Crianças.
- `privchat.html`: página completa do PrivChat e fluxo de instalação.
- `ajuda-instalacao.html`: resolução de problemas de download e instalação.
- `privchat-v2.png`: ícone atual do PrivChat. O nome versionado resolveu cache antigo do navegador/Cloudflare.
- `app.apk`: arquivo baixado pelo botão **Instalar**, apresentado ao navegador como `PrivChat.apk`.
- `store-runtime.js`: tratamento comum de falhas de recursos e arquivos.
- `fallback-app.svg`: imagem de fallback.
- `404.html`: página de erro.
- `server.py`: servidor HTTP Python exclusivo para `/store/`.
- `nginx-store.conf`: bloco Nginx que deve ficar dentro do `server { ... }` HTTPS já existente.
- `SERVIDOR.md`: instruções rápidas do servidor.

Também existe `51OLG+0NfPL.png`, nome antigo do ícone; as páginas atuais devem usar `privchat-v2.png`.

## Estado funcional atual

- A página inicial e as categorias simulam o visual da Google Play.
- Clicar no PrivChat abre `privchat.html`.
- O aplicativo mostra avaliação `4,7`, mais de `200 mil` downloads e comentários demonstrativos.
- O botão **Instalar** abre um modal de verificação visual com barra de progresso de aproximadamente cinco segundos.
- O modal informa explicitamente que é uma simulação e não uma análise real do Google Play Protect.
- Antes de iniciar o fluxo, o código confirma que `app.apk` está disponível.
- Depois da simulação, o navegador inicia o download do APK.
- Após o download ser iniciado, o modal permanece aberto e mostra:
  - **Problemas para instalar?**
  - link **Clique aqui para resolver · Resolução de problemas**.
- O link abre `./ajuda-instalacao.html`, preservando automaticamente o prefixo `/store/`.
- A página de ajuda cobre download interrompido, arquivo incompleto, armazenamento, compatibilidade, bloqueios do Android e conflito com versão existente.
- A página de ajuda não recomenda desativar o Play Protect ou ignorar alertas graves.
- Lista de desejos usa `localStorage` e possui tratamento caso o armazenamento não esteja disponível.

## Servidor local

Executar na raiz do projeto:

```powershell
cd F:\ProjetosCodeX\google-play-local
python server.py
```

Configuração padrão do `server.py`:

- host: `127.0.0.1`
- porta: `8181`
- prefixo obrigatório: `/store`

Alternativa explícita:

```powershell
python server.py --host 127.0.0.1 --port 8181
```

O servidor trata `/store`, `/store/`, arquivos inexistentes, tipos MIME, cache de HTML e download do APK. Não substituir por `python -m http.server`, pois isso perde o comportamento específico da subrota.

## Nginx

O domínio possui um serviço principal em outra porta, normalmente atrás de `location /`. O bloco da loja deve ser irmão de `location /`, nunca ficar aninhado dentro dele:

```nginx
location = /store {
    return 308 /store/;
}

location /store/ {
    proxy_pass http://127.0.0.1:8181/store/;
    proxy_http_version 1.1;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Prefix /store;

    proxy_connect_timeout 5s;
    proxy_read_timeout 60s;
}
```

Depois de editar:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Já ocorreu conflito porque havia dois arquivos habilitados com o mesmo `server_name`: `gemini_c2` e `gemini_backupconf`, sendo que o backup apontava para a mesma configuração. Manter apenas uma configuração habilitada para `updates-playstore.store`.

## Atualização pelo GitHub

O usuário prefere executar os commits e pushes; não commitar automaticamente.

No Windows:

```powershell
cd F:\ProjetosCodeX\google-play-local
git status
git add <arquivos-alterados>
git commit -m "Descrição da alteração"
git push
```

Na VPS:

```bash
cd /root/PlayStore
git pull --ff-only origin main
```

Arquivos estáticos novos normalmente aparecem sem reiniciar o servidor. Reiniciar somente se o processo/serviço não estiver respondendo ou se a forma de execução exigir isso.

## Diagnóstico na VPS

Verificar processo e porta:

```bash
ps aux | grep '[s]erver.py'
sudo ss -ltnp | grep ':8181'
curl -I http://127.0.0.1:8181/store/
curl -I http://127.0.0.1:8181/store/privchat-v2.png
curl -I http://127.0.0.1:8181/store/ajuda-instalacao.html
```

Verificar Nginx e acesso público:

```bash
sudo nginx -t
curl -kI https://updates-playstore.store/store/
curl -kI https://updates-playstore.store/store/privchat-v2.png
```

Se aparecer `Address already in use`, localizar o processo que já ocupa `8181` antes de iniciar outro. O serviço principal e a loja precisam usar portas locais diferentes.

## Cache e imagens

Cloudflare e o navegador já mantiveram uma versão antiga do ícone mesmo quando `curl` retornava HTTP 200. Renomear o recurso para `privchat-v2.png` e atualizar as referências resolveu o problema.

Ao alterar HTML ou imagens e a versão pública não mudar:

1. Confirmar o conteúdo diretamente com `curl`.
2. Fazer recarga forçada no navegador.
3. Limpar somente as URLs afetadas no cache do Cloudflare.
4. Para recursos visuais muito cacheados, preferir um novo nome versionado (`arquivo-v3.png`) ou query string de versão.

## Regras para próximas alterações

- Trabalhar a partir de `F:\ProjetosCodeX\google-play-local`.
- Preservar a publicação integral sob `/store/`.
- Usar links relativos como `./privchat.html`, `./app.apk` e `./privchat-v2.png`.
- Não usar caminhos iniciados por `/` para recursos internos.
- Não alterar nem interromper a plataforma principal do domínio.
- Manter acessibilidade básica: foco visível, textos alternativos, teclado e estados do modal.
- Manter tratamento de falhas para APK, imagens e navegação.
- Validar JavaScript e testar pelo menos as rotas alteradas com HTTP 200.
- Não incluir senhas, tokens, chaves privadas ou certificados no repositório.
- O usuário fará o commit e o push quando a alteração estiver pronta.

## Última alteração concluída

Foi adicionada a página `ajuda-instalacao.html`. O modal de instalação agora permanece aberto após iniciar o download e oferece o link de resolução de problemas. As seguintes rotas foram validadas localmente com HTTP 200:

- `/store/privchat.html`
- `/store/ajuda-instalacao.html`
- `/store/app.apk`

Até este ponto, o usuário confirmou que o projeto está funcionando corretamente.
