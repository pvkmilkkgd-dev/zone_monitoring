# РЎРєСЂРёРїС‚ РґР»СЏ СЃРѕР·РґР°РЅРёСЏ РїРѕР»РЅРѕРіРѕ Р°СЂС…РёРІР° РїСЂРѕРµРєС‚Р° СЃ Р±Р°Р·РѕР№ РґР°РЅРЅС‹С…
$ErrorActionPreference = "Stop"

# РџР°СЂР°РјРµС‚СЂС‹ Р±Р°Р·С‹ РґР°РЅРЅС‹С…
$DB_HOST = "localhost"
$DB_PORT = "5432"
$DB_NAME = "zone_monitoring"
$DB_USER = "zone_user"
$DB_PASSWORD = "Ural196User!"

# РџСѓС‚СЊ Рє РїСЂРѕРµРєС‚Сѓ
$PROJECT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKUP_DIR = Join-Path $PROJECT_DIR "backup"
$TIMESTAMP = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$BACKUP_NAME = "zone_monitoring_full_backup_$TIMESTAMP"
$BACKUP_PATH = Join-Path $BACKUP_DIR $BACKUP_NAME

Write-Host "РЎРѕР·РґР°РЅРёРµ РґРёСЂРµРєС‚РѕСЂРёРё РґР»СЏ Р±СЌРєР°РїР°..." -ForegroundColor Green
New-Item -ItemType Directory -Force -Path $BACKUP_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $BACKUP_PATH | Out-Null

# РџСЂРѕРІРµСЂСЏРµРј РЅР°Р»РёС‡РёРµ pg_dump
Write-Host "РџСЂРѕРІРµСЂРєР° РЅР°Р»РёС‡РёСЏ pg_dump..." -ForegroundColor Green
$pgDumpPath = Get-Command pg_dump -ErrorAction SilentlyContinue
if (-not $pgDumpPath) {
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
            Write-Host "РќР°Р№РґРµРЅ pg_dump: $path" -ForegroundColor Yellow
            break
        }
    }
    
    if (-not $found) {
        Write-Host "РћРЁРР‘РљРђ: pg_dump РЅРµ РЅР°Р№РґРµРЅ." -ForegroundColor Red
        exit 1
    }
}

# РЎРѕР·РґР°РµРј РґР°РјРї Р±Р°Р·С‹ РґР°РЅРЅС‹С…
Write-Host "РЎРѕР·РґР°РЅРёРµ РґР°РјРїР° Р±Р°Р·С‹ РґР°РЅРЅС‹С…..." -ForegroundColor Green
$dumpFile = Join-Path $BACKUP_PATH "database_dump.sql"

$env:PGPASSWORD = $DB_PASSWORD
try {
    $pgDumpArgs = @(
        "-h", $DB_HOST,
        "-p", $DB_PORT,
        "-U", $DB_USER,
        "-d", $DB_NAME,
        "-f", $dumpFile,
        "--no-owner",
        "--no-acl",
        "--clean",
        "--if-exists"
    )
    
    & pg_dump $pgDumpArgs
    
    if ($LASTEXITCODE -ne 0) {
        throw "pg_dump Р·Р°РІРµСЂС€РёР»СЃСЏ СЃ РѕС€РёР±РєРѕР№"
    }
    
    Write-Host "Р”Р°РјРї Р‘Р” СЃРѕР·РґР°РЅ: $dumpFile" -ForegroundColor Green
} catch {
    Write-Host "РћРЁРР‘РљРђ РїСЂРё СЃРѕР·РґР°РЅРёРё РґР°РјРїР° Р‘Р”: $_" -ForegroundColor Red
    exit 1
} finally {
    $env:PGPASSWORD = $null
}

# РљРѕРїРёСЂСѓРµРј С„Р°Р№Р»С‹ РїСЂРѕРµРєС‚Р°
Write-Host "РљРѕРїРёСЂРѕРІР°РЅРёРµ С„Р°Р№Р»РѕРІ РїСЂРѕРµРєС‚Р°..." -ForegroundColor Green

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
    "*.log",
    ".idea",
    ".vscode"
)

function Should-Exclude {
    param($Path)
    
    foreach ($pattern in $excludePatterns) {
        if ($Path -like "*\$pattern" -or $Path -like "*\$pattern\*" -or $Path -like "$pattern\*" -or $Path -like "*\$pattern") {
            return $true
        }
    }
    return $false
}

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

Write-Host "РЎРєРѕРїРёСЂРѕРІР°РЅРѕ С„Р°Р№Р»РѕРІ: $copied" -ForegroundColor Green

# РЎРѕР·РґР°РµРј С„Р°Р№Р» СЃ РёРЅС„РѕСЂРјР°С†РёРµР№ Рѕ Р±СЌРєР°РїРµ
$infoFile = Join-Path $BACKUP_PATH "BACKUP_INFO.txt"
$dateStr = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$infoContent = "Backup of Zone Monitoring project`r`n"
$infoContent += "Created: $dateStr`r`n"
$infoContent += "Database: PostgreSQL`r`n"
$infoContent += "DB Name: $DB_NAME`r`n"
$infoContent += "Host: ${DB_HOST}:${DB_PORT}`r`n`r`n"
$infoContent += "Restore DB:`r`n"
$infoContent += "1. Create database: CREATE DATABASE zone_monitoring;`r`n"
$infoContent += "2. Restore dump: psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f database_dump.sql`r`n`r`n"
$infoContent += "Restore dependencies:`r`n"
$infoContent += "Backend: cd backend && pip install -r requirements.txt`r`n"
$infoContent += "Frontend: cd frontend && npm install`r`n"
Set-Content -Path $infoFile -Value $infoContent -Encoding UTF8

# РЎРѕР·РґР°РµРј Р°СЂС…РёРІ
Write-Host "РЎРѕР·РґР°РЅРёРµ Р°СЂС…РёРІР°..." -ForegroundColor Green
$archivePath = "$BACKUP_PATH.zip"
Compress-Archive -Path "$BACKUP_PATH\*" -DestinationPath $archivePath -Force

Write-Host "РђСЂС…РёРІ СЃРѕР·РґР°РЅ: $archivePath" -ForegroundColor Green

$archiveSize = (Get-Item $archivePath).Length / 1MB
Write-Host "Р Р°Р·РјРµСЂ Р°СЂС…РёРІР°: $([math]::Round($archiveSize, 2)) MB" -ForegroundColor Green

# РЈРґР°Р»СЏРµРј РІСЂРµРјРµРЅРЅСѓСЋ РґРёСЂРµРєС‚РѕСЂРёСЋ
Write-Host "РћС‡РёСЃС‚РєР° РІСЂРµРјРµРЅРЅС‹С… С„Р°Р№Р»РѕРІ..." -ForegroundColor Green
Remove-Item -Path $BACKUP_PATH -Recurse -Force

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Р РµР·РµСЂРІРЅР°СЏ РєРѕРїРёСЏ СЃРѕР·РґР°РЅР° СѓСЃРїРµС€РЅРѕ!" -ForegroundColor Green
Write-Host "Р¤Р°Р№Р»: $archivePath" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Green