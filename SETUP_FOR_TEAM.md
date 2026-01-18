# 🚀 Инструкция для быстрого старта проекта

## Для новых разработчиков

### Требования
- Git установлен
- Docker Desktop установлен и запущен

---

## 📥 Шаг 1: Клонирование проекта

```bash
git clone https://github.com/pvkmilkkgd-dev/zone_monitoring.git
cd zone_monitoring
```

---

## 🐳 Шаг 2: Запуск через Docker (САМЫЙ ПРОСТОЙ способ)

```bash
docker-compose up --build
```

**Подождите 2-3 минуты** пока все контейнеры соберутся и запустятся.

### Что происходит:
1. 📦 Собирается образ backend (FastAPI)
2. 📦 Собирается образ frontend (React + Nginx)
3. 🗄️ Создается PostgreSQL БД
4. 📊 **Автоматически загружаются все данные** из дампа
5. 🚀 Запускаются все сервисы

---

## ✅ Шаг 3: Проверка работы

Откройте в браузере:

- **Frontend**: http://localhost
- **Backend API**: http://localhost:8000
- **API Документация**: http://localhost:8000/docs

### Тестовые данные для входа:
- Логин: `admin`
- Пароль: (спросите у команды)

---

## 🛠️ Для локальной разработки (рекомендуется)

Если хотите разрабатывать локально с hot reload:

### 1. Запустите ТОЛЬКО базу данных:
```bash
docker-compose up db
```

### 2. Backend (в отдельном терминале):
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend (в еще одном терминале):
```bash
cd frontend
npm install
npm run dev
```

**Настройки подключения к БД:**
- Host: `localhost`
- Port: `5433` (не 5432!)
- Database: `zone_monitoring`
- User: `zone_user`
- Password: `Ural196User!`

---

## 🔄 Обновление проекта

### Получить изменения от коллег:
```bash
git pull
```

### Если изменилась структура БД:
```bash
cd backend
alembic upgrade head
```

### Если обновился дамп данных:
```bash
docker-compose down -v  # Удалить старую БД
docker-compose up db    # Создать новую с новыми данными
```

---

## 🛑 Остановка проекта

```bash
# Остановить контейнеры
docker-compose down

# Остановить + удалить данные БД
docker-compose down -v
```

---

## 📝 Полезные команды

```bash
# Посмотреть логи всех сервисов
docker-compose logs -f

# Посмотреть логи конкретного сервиса
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db

# Перезапустить сервис
docker-compose restart backend

# Зайти в контейнер БД
docker-compose exec db psql -U zone_user -d zone_monitoring
```

---

## ❓ Проблемы?

### Порт уже занят:
Измените порты в `docker-compose.yml`:
```yaml
ports:
  - "8080:80"    # вместо 80:80 для frontend
  - "8001:8000"  # вместо 8000:8000 для backend
```

### Docker не установлен:
Скачайте с https://www.docker.com/products/docker-desktop/

### БД не запускается:
```bash
docker-compose down -v
docker-compose up db
```

---

## 💬 Контакты

Если что-то не работает - пишите в чат команды!
