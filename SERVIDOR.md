# Servidor local

O clone é servido exclusivamente sob a rota `/store/`.

## Iniciar

Na pasta do projeto, execute:

```powershell
python server.py
```

Depois abra `http://127.0.0.1:8181/store/`.

Para alterar endereço ou porta:

```powershell
python server.py --host 0.0.0.0 --port 8181
```

## Usar com Nginx

1. Mantenha o servidor Python ativo em `127.0.0.1:8181`.
2. Copie o conteúdo de `nginx-store.conf` para dentro do bloco `server { ... }` do seu site.
3. Valide e recarregue o Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

O clone ficará disponível em `https://seu-dominio/store/`. O botão **Instalar** baixa o arquivo local como `PrivChat.apk`.
