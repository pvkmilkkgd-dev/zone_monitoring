#!/usr/bin/env sh
set -eu

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

docker compose up -d --build
docker compose ps

echo "Done. Open: http://<SERVER_IP>:8080"
