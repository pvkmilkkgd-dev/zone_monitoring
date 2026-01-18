# Скрипт для создания резервной копии проекта с базой данных
# Автоматически создает дамп БД и архивирует весь проект

$ErrorActionPreference = "Stop"

# Параметры базы данных (из config.py)
$DB_HOST = "localhost"
$DB_PORT = "5432"
$DB_NAME = "zone_monitoring"
$DB_USER = "zone_user"
$DB_PASSWORD = "Ural196User!"

# Путь к проекту
$PROJECT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKUP_DIR = Join-Path $PROJECT_DIR "backup"
$TIMESTAMP = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$BACKUP_NAME = "zone_monitoring_backup_$TIMESTAMP"
$BACKUP_PATH = Join-Path $BACKUP_DIR $BACKUP_NAME

# Создаем директорию для бэкапа
Write-Host "Создание директории для бэкапа..." -ForegroundColor Green
New-Item -ItemType Directory -Force -Path $BACKUP_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $BACKUP_PATH | Out-Null

# Проверяем наличие pg_dump
Write-Host "Проверка наличия pg_dump..." -ForegroundColor Green
$pgDumpPath = Get-Command pg_dump -ErrorAction SilentlyContinue
if (-not $pgDumpPath) {
    # Пробуем найти в стандартных местах установки PostgreSQL
    $possiblePaths = @(
        "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\15\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\14\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\13\bin\pg_dump.exe"
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
        Write-Host "ОШИБКА: pg_dump не найден. Убедитесь, что PostgreSQL установлен и добавлен в PATH." -ForegroundColor Red
        Write-Host "Или укажите путь к pg_dump вручную в скрипте." -ForegroundColor Red
        exit 1
    }
}

# Создаем дамп базы данных
Write-Host "Создание дампа базы данных..." -ForegroundColor Green
$dumpFile = Join-Path $BACKUP_PATH "database_dump.sql"

$env:PGPASSWORD = $DB_PASSWORD
try {
    $pgDumpArgs = @(
        "-h", $DB_HOST,
        "-p", $DB_PORT,
        "-U", $DB_USER,
        "-d", $DB_NAME,
        "-F", "c",  # Custom format (сжатый)
        "-f", $dumpFile,
        "--no-owner",
        "--no-acl"
    )
    
    & pg_dump $pgDumpArgs
    
    if ($LASTEXITCODE -ne 0) {
        throw "pg_dump завершился с ошибкой"
    }
    
    Write-Host "Дамп БД создан: $dumpFile" -ForegroundColor Green
} catch {
    Write-Host "ОШИБКА при создании дампа БД: $_" -ForegroundColor Red
    Write-Host "Попытка создать дамп в текстовом формате..." -ForegroundColor Yellow
    
    # Пробуем текстовый формат
    $dumpFileTxt = Join-Path $BACKUP_PATH "database_dump.sql"
    $pgDumpArgs = @(
        "-h", $DB_HOST,
        "-p", $DB_PORT,
        "-U", $DB_USER,
        "-d", $DB_NAME,
        "-f", $dumpFileTxt,
        "--no-owner",
        "--no-acl"
    )
    
    & pg_dump $pgDumpArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ОШИБКА: Не удалось создать дамп БД. Проверьте подключение к БД." -ForegroundColor Red
        exit 1
    }
    
    $dumpFile = $dumpFileTxt
    Write-Host "Дамп БД создан в текстовом формате: $dumpFile" -ForegroundColor Green
} finally {
    $env:PGPASSWORD = $null
}

# Копируем файлы проекта (исключая node_modules, __pycache__, .git и т.д.)
Write-Host "Копирование файлов проекта..." -ForegroundColor Green

# Создаем список исключений
$excludePatterns = @(
    "node_modules",
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    ".env",
    "*.pyc",
    "*.pyo",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    ".next",
    ".vite",
    "backup",
    "*.log"
)

# Функция для проверки, нужно ли исключить путь
function Should-Exclude {
    param($Path)
    
    foreach ($pattern in $excludePatterns) {
        if ($Path -like "*\$pattern" -or $Path -like "*\$pattern\*" -or $Path -like "*.log") {
            return $true
        }
    }
    return $false
}

# Копируем файлы
$copied = 0
Get-ChildItem -Path $PROJECT_DIR -Recurse -File | ForEach-Object {
    $relativePath = $_.FullName.Substring($PROJECT_DIR.Length + 1)
    
    if (-not (Should-Exclude $relativePath)) {
        $destPath = Join-Path $BACKUP_PATH $relativePath
        $destDir = Split-Path -Parent $destPath
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        Copy-Item $_.FullName -Destination $destPath -Force
        $copied++
    }
}

Write-Host "Скопировано файлов: $copied" -ForegroundColor Green

# Создаем файл с информацией о бэкапе
$infoFile = Join-Path $BACKUP_PATH "BACKUP_INFO.txt"
$dateStr = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$infoContent = "Backup of Zone Monitoring project`r`n"
$infoContent += "Created: $dateStr`r`n"
$infoContent += "Database: PostgreSQL`r`n"
$infoContent += "DB Name: $DB_NAME`r`n"
$infoContent += "Host: ${DB_HOST}:${DB_PORT}`r`n`r`n"
$infoContent += "Restore DB:`r`n"
$infoContent += "1. Create database: CREATE DATABASE zone_monitoring;`r`n"
$infoContent += "2. Restore dump:`r`n"
$infoContent += "   - Custom format: pg_restore -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME database_dump.sql`r`n"
$infoContent += "   - Text format: psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f database_dump.sql`r`n`r`n"
$infoContent += "Or use restore_backup.ps1 script`r`n"
Set-Content -Path $infoFile -Value $infoContent -Encoding UTF8

# Create archive
Write-Host "Creating archive..." -ForegroundColor Green
$archivePath = "$BACKUP_PATH.zip"

# Use Compress-Archive (built-in PowerShell cmdlet)
Compress-Archive -Path "$BACKUP_PATH\*" -DestinationPath $archivePath -Force

Write-Host "Archive created: $archivePath" -ForegroundColor Green

# Show archive size
$archiveSize = (Get-Item $archivePath).Length / 1MB
Write-Host "Archive size: $([math]::Round($archiveSize, 2)) MB" -ForegroundColor Green

# Remove temporary directory
Write-Host "Cleaning up temporary files..." -ForegroundColor Green
Remove-Item -Path $BACKUP_PATH -Recurse -Force

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Backup created successfully!" -ForegroundColor Green
Write-Host "File: $archivePath" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Green
