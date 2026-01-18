#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для создания полного архива проекта с базой данных
"""

import os
import sys
import subprocess
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

# Параметры базы данных
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "zone_monitoring"
DB_USER = "zone_user"
DB_PASSWORD = "Ural196User!"

# Альтернативный пользователь для дампа (если zone_user не имеет достаточных прав)
# Раскомментируйте и укажите данные суперпользователя при необходимости:
# DB_USER = "postgres"
# DB_PASSWORD = "your_postgres_password"

# Путь к проекту
PROJECT_DIR = Path(__file__).parent.absolute()
BACKUP_DIR = PROJECT_DIR / "backup"
TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
BACKUP_NAME = f"zone_monitoring_full_backup_{TIMESTAMP}"
BACKUP_PATH = BACKUP_DIR / BACKUP_NAME

# Паттерны для исключения
EXCLUDE_PATTERNS = [
    "node_modules",
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    ".env",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    ".next",
    ".vite",
    "backup",
    ".idea",
    ".vscode",
    ".gitignore",
]


def should_exclude(path: Path) -> bool:
    """Проверяет, нужно ли исключить путь из архива"""
    path_str = str(path)
    for pattern in EXCLUDE_PATTERNS:
        if pattern in path_str:
            return True
    # Исключаем файлы с расширениями
    if path.suffix in [".pyc", ".pyo", ".log"]:
        return True
    return False


def find_pg_dump():
    """Находит путь к pg_dump"""
    # Проверяем в PATH
    try:
        result = subprocess.run(
            ["pg_dump", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        return "pg_dump"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Проверяем стандартные пути установки PostgreSQL
    possible_paths = [
        r"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\14\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\13\bin\pg_dump.exe",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def create_database_dump(dump_file: Path):
    """Создает дамп базы данных"""
    print("Создание дампа базы данных...")
    
    pg_dump_path = find_pg_dump()
    if not pg_dump_path:
        print("ПРЕДУПРЕЖДЕНИЕ: pg_dump не найден. Пропускаем создание дампа БД.")
        print("Вы можете создать дамп вручную командой:")
        print(f"  pg_dump -h {DB_HOST} -p {DB_PORT} -U {DB_USER} -d {DB_NAME} -f database_dump.sql")
        return False
    
    # Устанавливаем переменную окружения для пароля
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD
    
    # Команда для создания дампа
    # Используем опции для обхода проблем с правами доступа
    # Пробуем создать дамп с опцией --no-tablespaces и игнорированием ошибок блокировки
    cmd = [
        pg_dump_path,
        "-h", DB_HOST,
        "-p", DB_PORT,
        "-U", DB_USER,
        "-d", DB_NAME,
        "-f", str(dump_file),
        "--no-owner",
        "--no-acl",
        "--no-privileges",
        "--no-tablespaces",
        "--clean",
        "--if-exists",
    ]
    
    # Если есть проблемы с правами, можно попробовать использовать суперпользователя
    # Для этого раскомментируйте следующие строки и укажите пароль postgres:
    # print("Попытка создания дампа с текущим пользователем...")
    # print("Если возникнут ошибки прав доступа, используйте пользователя postgres")
    
    try:
        # Используем encoding='utf-8' и errors='ignore' для обработки вывода
        result = subprocess.run(
            cmd, 
            env=env, 
            check=False,  # Не прерываем выполнение при ошибках
            capture_output=True, 
            encoding='utf-8',
            errors='ignore'
        )
        
        # Проверяем, был ли создан файл дампа
        if dump_file.exists() and dump_file.stat().st_size > 0:
            print(f"Дамп БД создан: {dump_file}")
            if result.returncode != 0 and result.stderr:
                print(f"Предупреждения при создании дампа: {result.stderr[:500]}")
            return True
        else:
            print(f"ОШИБКА: Файл дампа не был создан или пуст")
            if result.stderr:
                print(f"Ошибка: {result.stderr}")
            return False
    except Exception as e:
        print(f"Неожиданная ошибка при создании дампа БД: {e}")
        return False


def copy_project_files(dest_path: Path):
    """Копирует файлы проекта в директорию бэкапа"""
    print("Копирование файлов проекта...")
    
    copied = 0
    for root, dirs, files in os.walk(PROJECT_DIR):
        # Исключаем директории из списка для обхода
        dirs[:] = [d for d in dirs if not should_exclude(Path(root) / d)]
        
        for file in files:
            src_file = Path(root) / file
            if should_exclude(src_file):
                continue
            
            # Вычисляем относительный путь
            try:
                relative_path = src_file.relative_to(PROJECT_DIR)
            except ValueError:
                continue
            
            dest_file = dest_path / relative_path
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                shutil.copy2(src_file, dest_file)
                copied += 1
            except Exception as e:
                print(f"Ошибка при копировании {src_file}: {e}")
    
    print(f"Скопировано файлов: {copied}")
    return copied


def create_backup_info(dest_path: Path):
    """Создает файл с информацией о бэкапе"""
    info_file = dest_path / "BACKUP_INFO.txt"
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    info_content = f"""Backup of Zone Monitoring project
Created: {date_str}
Database: PostgreSQL
DB Name: {DB_NAME}
Host: {DB_HOST}:{DB_PORT}

Restore DB:
1. Create database: CREATE DATABASE zone_monitoring;
2. Restore dump: psql -h {DB_HOST} -p {DB_PORT} -U {DB_USER} -d {DB_NAME} -f database_dump.sql

Or use restore_backup.ps1 script

Restore dependencies:
Backend: cd backend && pip install -r requirements.txt
Frontend: cd frontend && npm install
"""
    
    with open(info_file, "w", encoding="utf-8") as f:
        f.write(info_content)
    
    print(f"Файл информации создан: {info_file}")


def create_archive(source_path: Path, archive_path: Path):
    """Создает ZIP архив"""
    print("Создание архива...")
    
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_path):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(source_path)
                zipf.write(file_path, arcname)
    
    archive_size = archive_path.stat().st_size / (1024 * 1024)  # MB
    print(f"Архив создан: {archive_path}")
    print(f"Размер архива: {archive_size:.2f} MB")


def main():
    """Основная функция"""
    print("=" * 50)
    print("Создание резервной копии проекта")
    print("=" * 50)
    
    # Создаем директории
    print("Создание директории для бэкапа...")
    BACKUP_DIR.mkdir(exist_ok=True)
    BACKUP_PATH.mkdir(exist_ok=True)
    
    # Создаем дамп БД
    dump_file = BACKUP_PATH / "database_dump.sql"
    if not create_database_dump(dump_file):
        print("ПРЕДУПРЕЖДЕНИЕ: Не удалось создать дамп БД. Продолжаем без него...")
    
    # Копируем файлы проекта
    copy_project_files(BACKUP_PATH)
    
    # Создаем файл информации
    create_backup_info(BACKUP_PATH)
    
    # Создаем архив
    archive_path = BACKUP_DIR / f"{BACKUP_NAME}.zip"
    create_archive(BACKUP_PATH, archive_path)
    
    # Удаляем временную директорию
    print("Очистка временных файлов...")
    shutil.rmtree(BACKUP_PATH)
    
    print("")
    print("=" * 50)
    print("Резервная копия создана успешно!")
    print(f"Файл: {archive_path}")
    print("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nПрервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\nОшибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
