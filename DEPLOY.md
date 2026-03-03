# Deploy (Simple)

## Requirements
- Docker Desktop (Windows) or Docker Engine + Docker Compose (Linux)
- Open port `8080` on the server firewall (or change `APP_PORT` in `.env`)

## 1) Prepare environment file
From project root:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set secure values:
- `POSTGRES_PASSWORD`
- `SECRET_KEY`

## 2) Run the project

```bash
docker compose up -d --build
```

## 3) Check status

```bash
docker compose ps
docker compose logs -f app
```

## URL
Open:

`http://<SERVER_IP>:8080`

---

## Useful commands

Stop:

```bash
docker compose down
```

Restart:

```bash
docker compose restart
```

Update after code changes:

```bash
docker compose up -d --build
```
