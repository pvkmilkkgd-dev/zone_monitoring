# Скрипт для создания дампа БД с использованием суперпользователя postgres
$ErrorActionPreference = "Stop"

# Параметры базы данных
$DB_HOST = "localhost"
$DB_PORT = "5432"
$DB_NAME = "zone_monitoring"
$DB_USER = "postgres"  # Используем суперпользователя
$DB_PASSWORD = Read-Host "Введите пароль пользователя postgres" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($DB_PASSWORD)
$DB_PASSWORD_PLAIN = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

# Путь к проекту
$PROJECT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKUP_DIR = Join-Path $PROJECT_DIR "backup"
$TIMESTAMP = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$DUMP_FILE = Join-Path $BACKUP_DIR "database_dump_$TIMESTAMP.sql"

Write-Host "Создание дампа базы данных..." -ForegroundColor Green

# Проверяем наличие pg_dump
$pgDumpPath = Get-Command pg_dump -ErrorAction SilentlyContinue
if (-not $pgDumpPath) {
    $possiblePaths = @(
        "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\17\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\15\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\14\bin\pg_dump.exe"
    )
    
    $found = $false
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $env:Path += ";$(Split-Path -Parent $path)"
            $found = $true
            Write-Host "Найден pg_dump: $path" -ForegroundColor Yellow
            break
        }
    }
    
    if (-not $found) {
        Write-Host "ОШИБКА: pg_dump не найден." -ForegroundColor Red
        exit 1
    }
}

# Создаем директорию для дампа
New-Item -ItemType Directory -Force -Path $BACKUP_DIR | Out-Null

# Создаем дамп
$env:PGPASSWORD = $DB_PASSWORD_PLAIN
try {
    $pgDumpArgs = @(
        "-h", $DB_HOST,
        "-p", $DB_PORT,
        "-U", $DB_USER,
        "-d", $DB_NAME,
        "-f", $DUMP_FILE,
        "--no-owner",
        "--no-acl",
        "--no-privileges",
        "--no-tablespaces",
        "--clean",
        "--if-exists"
    )
    
    & pg_dump $pgDumpArgs
    
    if ($LASTEXITCODE -ne 0) {
        throw "pg_dump завершился с ошибкой"
    }
    
    $fileSize = (Get-Item $DUMP_FILE).Length / 1MB
    Write-Host ""
    Write-Host "Дамп БД создан успешно!" -ForegroundColor Green
    Write-Host "Файл: $DUMP_FILE" -ForegroundColor Cyan
    Write-Host "Размер: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Cyan
} catch {
    Write-Host "ОШИБКА при создании дампа БД: $_" -ForegroundColor Red
    exit 1
} finally {
    $env:PGPASSWORD = $null
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
}
