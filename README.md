# Zone Monitoring System

Система мониторинга зон с картами и событиями. Full-stack приложение на FastAPI и React.

## 🚀 Возможности

- **Мониторинг зон** - отслеживание состояния различных зон на карте
- **Управление событиями** - создание и управление событиями по зонам
- **Работа с картами** - поддержка GeoJSON карт регионов
- **Система ролей** - viewer, editor, admin
- **Аутентификация** - JWT-токены для безопасного доступа
- **REST API** - полный RESTful API с документацией

## 📋 Требования

- Python 3.10+
- Node.js 18+
- PostgreSQL 12+
- pip и npm

## 🔧 Установка

### Backend

1. Установите зависимости:
```bash
cd backend
pip install -r requirements.txt
```

2. Создайте файл `.env` в директории `backend/` (опционально):
```env
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/zone_monitoring
SECRET_KEY=your-secret-key-here
BACKEND_CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

3. Настройте базу данных и запустите миграции:
```bash
# Убедитесь, что PostgreSQL запущен и база данных создана
alembic upgrade head
```

4. Запустите сервер:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend будет доступен на `http://127.0.0.1:8000`

### Frontend

1. Установите зависимости:
```bash
cd frontend
npm install
```

2. Для разработки:
```bash
npm run dev
```
Frontend будет доступен на `http://localhost:5173`

3. Для production (сборка):
```bash
npm run build
```
Собранные файлы будут в `frontend/dist/` и будут обслуживаться через FastAPI.

## 📖 Использование

### Первый запуск

1. Запустите backend сервер
2. Откройте браузер на `http://127.0.0.1:8000`
3. Если в системе еще нет пользователей, вы будете перенаправлены на страницу первоначальной настройки (`/setup`)
4. Создайте первого администратора
5. После этого вы сможете войти в систему

### API Документация

После запуска backend доступна интерактивная документация:
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

### Основные эндпоинты

- `GET /ping` - проверка работоспособности
- `POST /api/v1/auth/token` - получение JWT токена
- `GET /api/v1/auth/status` - проверка статуса инициализации
- `POST /api/v1/auth/bootstrap` - создание первого администратора

## 🗂️ Структура проекта

```
zone_monitoring/
├── backend/              # Backend (FastAPI)
│   ├── app/
│   │   ├── api/         # API роуты
│   │   ├── core/        # Конфигурация, безопасность
│   │   ├── db/          # База данных
│   │   ├── models/      # SQLAlchemy модели
│   │   ├── schemas/     # Pydantic схемы
│   │   ├── services/    # Бизнес-логика
│   │   └── main.py      # Точка входа
│   ├── migrations/      # Alembic миграции
│   ├── maps/            # GeoJSON карты
│   └── requirements.txt
├── frontend/            # Frontend (React + TypeScript)
│   ├── src/
│   │   ├── api/         # API клиенты
│   │   ├── components/  # React компоненты
│   │   ├── pages/       # Страницы
│   │   └── App.tsx
│   └── package.json
└── README.md
```

## 🔐 Безопасность

- Пароли хешируются с помощью bcrypt
- JWT токены для аутентификации
- Система ролей для контроля доступа
- CORS настроен (по умолчанию разрешены все источники для разработки)

**Внимание**: Для production обязательно:
1. Измените `SECRET_KEY` на безопасный случайный ключ
2. Ограничьте `BACKEND_CORS_ORIGINS` только нужными доменами
3. Используйте HTTPS
4. Не храните пароли БД в коде

## 🛠️ Разработка

### Миграции базы данных

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "описание изменений"

# Применить миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1
```

### Тестирование

```bash
# Проверка импорта приложения
python -c "from app.main import app; print('OK')"
```

## 📝 TODO

См. комментарии `TODO` в коде для планов развития:
- Реализация реальных запросов к БД в сервисах
- Добавление тестов
- Улучшение обработки ошибок
- Расширение валидации данных

## 📄 Лицензия

[Укажите вашу лицензию]

## 👥 Авторы

[Ваше имя/команда]

---

**Версия**: 0.1.0
