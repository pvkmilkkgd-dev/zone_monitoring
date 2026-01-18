# Docker запуск проекта Zone Monitoring

## Требования
- Docker Desktop установлен и запущен
- Порты 80, 8000, 5433 свободны

## Запуск проекта

### 1. Сборка и запуск всех контейнеров:
```bash
docker-compose up --build
```

### 2. Запуск в фоновом режиме:
```bash
docker-compose up -d --build
```

### 3. Остановка контейнеров:
```bash
docker-compose down
```

### 4. Остановка с удалением volumes (БД):
```bash
docker-compose down -v
```

## Доступные сервисы

- **Frontend**: http://localhost
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5433 (внешний порт)

## Структура

- `db` - PostgreSQL 16 с автоматической инициализацией из dump
- `backend` - FastAPI приложение на Python
- `frontend` - Vite/React приложение на Nginx

## База данных

База данных автоматически инициализируется из файла `backend/init_db.sql` при первом запуске.

Все данные сохраняются в Docker volume `postgres_data`.

## Логи

Просмотр логов всех сервисов:
```bash
docker-compose logs -f
```

Просмотр логов конкретного сервиса:
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

## Перезапуск сервиса

```bash
docker-compose restart backend
docker-compose restart frontend
```

## Troubleshooting

Если порты заняты, измените их в docker-compose.yml:
```yaml
ports:
  - "8080:80"    # вместо 80:80
  - "8001:8000"  # вместо 8000:8000
```
