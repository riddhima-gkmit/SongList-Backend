## Docker deployment notes

### Services

- **web**: Django + Gunicorn app (`songlist_backend.wsgi:application`), listens on port 8000 inside the network.
- **db**: PostgreSQL 16 (`DATABASE_HOST=db` in `.env`).
- **redis**: Redis 7 (`REDIS_URL=redis://redis:6379/...`).
- **celery-worker**: Celery worker (`celery -A songlist_backend worker`).
- **celery-beat**: Celery beat scheduler (`celery -A songlist_backend beat`).
- **nginx**: Reverse proxy in front of `web` (ports 80/443).
- **certbot**: For issuing/renewing Let's Encrypt certificates.

### First-time HTTPS setup (manual example)

1. Make sure DNS for your domain points to the server running Docker.
2. Start the stack (HTTP only) so Nginx can serve the ACME challenge:

```bash
docker compose up -d web db redis celery-worker celery-beat nginx
```

3. Run Certbot (replace `yourdomain.com` and email):

```bash
docker compose run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d yourdomain.com \
  --email you@example.com \
  --agree-tos \
  --no-eff-email
```

4. After certificates are issued under `deploy/nginx/certbot/conf`, update the Nginx config to add the TLS `server` block and reload:

```bash
docker compose restart nginx
```

5. For renewal, you can set up a cron job on the host:

```bash
0 3 * * * cd /path/to/SongList-Backend && docker compose run --rm certbot renew && docker compose restart nginx
```

