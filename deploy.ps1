$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
}

docker compose up -d --build
docker compose ps

Write-Host "Done. Open: http://<SERVER_IP>:8080"
