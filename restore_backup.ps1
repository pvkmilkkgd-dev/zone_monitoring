# Скрипт для восстановления проекта из резервной копии
# Использование: .\restore_backup.ps1 -BackupFile "путь_к_архиву.zip"

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupFile
)

$ErrorActionPreference = "Stop"

# Параметры базы данных
$DB_HOST = "localhost"
$DB_PORT = "5432"
$DB_NAME = "zone_monitoring"
$DB_USER = "zone_user"
$DB_PASSWORD = "Ural196User!"

Write-Host "Восстановление из резервной копии: $BackupFile" -ForegroundColor Green

# Проверяем наличие архива
if (-not (Test-Path $BackupFile)) {
    Write-Host "ОШИБКА: Файл архива не найден: $BackupFile" -ForegroundColor Red
    exit 1
}

# Распаковываем архив
$tempDir = Join-Path $env:TEMP "restore_backup_$(Get-Date -Format 'yyyyMMddHHmmss')"
Write-Host "Распаковка архива во временную директорию..." -ForegroundColor Green
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
Expand-Archive -Path $BackupFile -DestinationPath $tempDir -Force

# Ищем файл дампа БД
$dumpFile = Get-ChildItem -Path $tempDir -Recurse -Filter "database_dump.sql" | Select-Object -First 1

if (-not $dumpFile) {
    Write-Host "ОШИБКА: Файл дампа БД не найден в архиве" -ForegroundColor Red
    Remove-Item -Path $tempDir -Recurse -Force
    exit 1
}

Write-Host "Найден дамп БД: $($dumpFile.FullName)" -ForegroundColor Green

# Проверяем наличие psql/pg_restore
Write-Host "Проверка наличия PostgreSQL клиента..." -ForegroundColor Green
$psqlPath = Get-Command psql -ErrorAction SilentlyContinue
$pgRestorePath = Get-Command pg_restore -ErrorAction SilentlyContinue

if (-not $psqlPath -and -not $pgRestorePath) {
    $possiblePaths = @(
        "C:\Program Files\PostgreSQL\16\bin",
        "C:\Program Files\PostgreSQL\15\bin",
        "C:\Program Files\PostgreSQL\14\bin",
        "C:\Program Files\PostgreSQL\13\bin"
    )
    
    $found = $false
    foreach ($path in $possiblePaths) {
        if (Test-Path "$path\psql.exe") {
            $env:Path += ";$path"
            $found = $true
            Write-Host "Найден PostgreSQL клиент: $path" -ForegroundColor Yellow
            break
        }
    }
    
    if (-not $found) {
        Write-Host "ОШИБКА: PostgreSQL клиент не найден. Убедитесь, что PostgreSQL установлен." -ForegroundColor Red
        Remove-Item -Path $tempDir -Recurse -Force
        exit 1
    }
}

# Создаем базу данных (если не существует)
Write-Host "Проверка существования базы данных..." -ForegroundColor Green
$env:PGPASSWORD = $DB_PASSWORD

try {
    # Проверяем существование БД
    $dbExists = & psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>&1
    
    if ($dbExists -match "1") {
        Write-Host "База данных уже существует. Удаление старой БД..." -ForegroundColor Yellow
        
        # Закрываем все соединения
        & psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" 2>&1 | Out-Null
        
        # Удаляем БД
        & psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>&1 | Out-Null
    }
    
    # Создаем новую БД
    Write-Host "Создание базы данных..." -ForegroundColor Green
    & psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME;" 2>&1 | Out-Null
    
    if ($LASTEXITCODE -ne 0) {
        throw "Не удалось создать базу данных"
    }
    
    # Восстанавливаем дамп
    Write-Host "Восстановление дампа БД..." -ForegroundColor Green
    
    # Проверяем формат файла (custom или plain)
    $fileContent = Get-Content $dumpFile.FullName -Raw -ErrorAction SilentlyContinue
    
    if ($fileContent -match "PostgreSQL database dump" -or $fileContent.Length -lt 1000) {
        # Это текстовый формат
        Write-Host "Обнаружен текстовый формат дампа" -ForegroundColor Yellow
        & psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $dumpFile.FullName 2>&1 | Out-Null
    } else {
        # Пробуем custom формат
        Write-Host "Попытка восстановления в custom формате..." -ForegroundColor Yellow
        & pg_restore -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME --no-owner --no-acl $dumpFile.FullName 2>&1 | Out-Null
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Custom формат не подошел, пробуем текстовый..." -ForegroundColor Yellow
            & psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $dumpFile.FullName 2>&1 | Out-Null
        }
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ПРЕДУПРЕЖДЕНИЕ: Возможны ошибки при восстановлении БД. Проверьте логи выше." -ForegroundColor Yellow
    } else {
        Write-Host "База данных успешно восстановлена!" -ForegroundColor Green
    }
    
} catch {
    Write-Host "ОШИБКА при восстановлении БД: $_" -ForegroundColor Red
    Remove-Item -Path $tempDir -Recurse -Force
    exit 1
} finally {
    $env:PGPASSWORD = $null
}

# Очистка
Write-Host "Очистка временных файлов..." -ForegroundColor Green
Remove-Item -Path $tempDir -Recurse -Force

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Восстановление завершено!" -ForegroundColor Green
Write-Host "База данных: $DB_NAME" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Green
