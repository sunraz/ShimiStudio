# ShimiStudio Bootstrapper
# ========================
# הפעלה: קליק ימני → "הפעל עם PowerShell"
# או: powershell -ExecutionPolicy Bypass -File install_shimistudio.ps1
#
# הסקריפט הזה רק מתקין Python (אם חסר) ואז מריץ את המתקין האמיתי (Python)

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ShimiStudio - Bootstrapper" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# תיקיית התקנה
$INSTALL_DIR = "$env:USERPROFILE\ShimiStudio"
if (!(Test-Path $INSTALL_DIR)) { New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null }

# ═══ בדיקת Python ═══
Write-Host "[1/3] בודק Python..." -ForegroundColor Cyan
$pythonFound = $false

# נסה python
try {
    $pyVer = & python --version 2>&1
    if ($pyVer -match "Python") {
        Write-Host "  נמצא: $pyVer" -ForegroundColor Green
        $pythonFound = $true
    }
} catch {}

# נסה py launcher
if (-not $pythonFound) {
    try {
        $pyVer = & py -3 --version 2>&1
        if ($pyVer -match "Python") {
            Write-Host "  נמצא: $pyVer (via py launcher)" -ForegroundColor Green
            $pythonFound = $true
        }
    } catch {}
}

# נסה נתיבים מקובעים
if (-not $pythonFound) {
    $pyPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "C:\Python311\python.exe",
        "C:\Python312\python.exe",
        "C:\Program Files\Python311\python.exe",
        "C:\Program Files\Python312\python.exe"
    )
    foreach ($p in $pyPaths) {
        if (Test-Path $p) {
            $pyVer = & $p --version 2>&1
            if ($pyVer -match "Python") {
                Write-Host "  נמצא: $pyVer ב $p" -ForegroundColor Green
                $env:Path = "$env:Path;$p"
                $pythonFound = $true
                break
            }
        }
    }
}

# התקנת Python
if (-not $pythonFound) {
    Write-Host "  Python לא מותקן. מוריד ומתקין..." -ForegroundColor Yellow
    
    # נסה winget
    Write-Host "  מנסה winget..." -ForegroundColor Gray
    $wingetResult = & winget install Python.Python.3.11 -e --accept-package-agreements --accept-source-agreements 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Python הותקן דרך winget" -ForegroundColor Green
        $pythonFound = $true
    } else {
        Write-Host "  winget נכשל, מוריד ישירות..." -ForegroundColor Gray
        $pyInstaller = "$env:TEMP\python-installer.exe"
        try {
            Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" -OutFile $pyInstaller -UseBasicParsing
            Write-Host "  מתקין Python (חלון ייפתח)..." -ForegroundColor Gray
            $proc = Start-Process -FilePath $pyInstaller -ArgumentList "/passive","InstallAllUsers=1","PrependPath=1" -Wait -PassThru
            Remove-Item $pyInstaller -ErrorAction SilentlyContinue
            
            if ($proc.ExitCode -eq 0) {
                # רענן PATH
                $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
                Start-Sleep -Seconds 2
                
                # בדוק שוב
                try {
                    $pyVer = & python --version 2>&1
                    if ($pyVer -match "Python") {
                        Write-Host "  Python הותקן: $pyVer" -ForegroundColor Green
                        $pythonFound = $true
                    }
                } catch {}
            }
        } catch {
            Write-Host "  שגיאה בהורדת Python: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

if (-not $pythonFound) {
    Write-Host ""
    Write-Host "נכשלה התקנת Python!" -ForegroundColor Red
    Write-Host "נא להתקין Python ידנית מ: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "ואז להריץ שוב את הסקריפט הזה." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "לחץ ENTER לסגירה"
    exit 1
}

# ═══ בדיקת Git ═══
Write-Host ""
Write-Host "[2/3] בודק Git..." -ForegroundColor Cyan
$gitFound = $false
try {
    $gitVer = & git --version 2>&1
    if ($gitVer -match "git") {
        Write-Host "  נמצא: $gitVer" -ForegroundColor Green
        $gitFound = $true
    }
} catch {}

if (-not $gitFound) {
    Write-Host "  Git לא מותקן. מתקין..." -ForegroundColor Yellow
    $wingetResult = & winget install Git.Git -e --accept-package-agreements --accept-source-agreements 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Git הותקן דרך winget" -ForegroundColor Green
        $gitFound = $true
    } else {
        try {
            $gitInstaller = "$env:TEMP\git-installer.exe"
            Invoke-WebRequest -Uri "https://github.com/git-for-windows/git/releases/download/v2.45.0.windows.1/Git-2.45.0-64-bit.exe" -OutFile $gitInstaller -UseBasicParsing
            Start-Process -FilePath $gitInstaller -ArgumentList "/VERYSILENT","/NORESTART" -Wait
            Remove-Item $gitInstaller -ErrorAction SilentlyContinue
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            Write-Host "  Git הותקן" -ForegroundColor Green
            $gitFound = $true
        } catch {
            Write-Host "  נכשל - נא להתקין ידנית מ https://git-scm.com" -ForegroundColor Red
        }
    }
}

# ═══ הורדת והרצת המתקין האמיתי ═══
Write-Host ""
Write-Host "[3/3] מוריד ומריץ מתקין..." -ForegroundColor Cyan

$installerUrl = "https://raw.githubusercontent.com/sunraz/ShimiStudio/main/install_shimistudio.py"
$installerPath = "$INSTALL_DIR\install_shimistudio.py"

try {
    Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing
    Write-Host "  מתקין הורד" -ForegroundColor Green
} catch {
    Write-Host "  נכשלה הורדה מ GitHub. נסה שוב מאוחר יותר." -ForegroundColor Red
    Read-Host "לחץ ENTER לסגירה"
    exit 1
}

Write-Host "  מריץ מתקין..." -ForegroundColor Green
Write-Host ""
& python $installerPath

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "המתקין נתקל בשגיאה. קוד: $LASTEXITCODE" -ForegroundColor Yellow
}

Write-Host ""
Read-Host "לחץ ENTER לסגירה"
