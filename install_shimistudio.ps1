# ShimiStudio Bootstrapper
# ========================
# הפעלה: קליק ימני → "הפעל עם PowerShell"
# או: powershell -ExecutionPolicy Bypass -File install_shimistudio.ps1

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

# ═══ מצא Python — כל דרך אפשרית ═══
Write-Host "[1/3] מחפש Python..." -ForegroundColor Cyan

$pythonCmd = $null

# נסה python
try {
    $pyVer = & python --version 2>&1
    if ($pyVer -match "Python") {
        Write-Host "  נמצא: $pyVer" -ForegroundColor Green
        $pythonCmd = "python"
    }
} catch {}

# נסה py launcher
if (-not $pythonCmd) {
    try {
        $pyVer = & py -3 --version 2>&1
        if ($pyVer -match "Python") {
            Write-Host "  נמצא: $pyVer (via py launcher)" -ForegroundColor Green
            $pythonCmd = "py -3"
        }
    } catch {}
}

# נסה נתיבים ידועים
if (-not $pythonCmd) {
    $pyPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "C:\Python311\python.exe",
        "C:\Python312\python.exe",
        "C:\Python313\python.exe",
        "C:\Program Files\Python311\python.exe",
        "C:\Program Files\Python312\python.exe",
        "C:\Program Files\Python313\python.exe"
    )
    foreach ($p in $pyPaths) {
        if (Test-Path $p) {
            $pyVer = & $p --version 2>&1
            if ($pyVer -match "Python") {
                Write-Host "  נמצא: $pyVer ב $p" -ForegroundColor Green
                $pythonCmd = $p
                break
            }
        }
    }
}

# התקנת Python
if (-not $pythonCmd) {
    Write-Host "  Python לא מותקן. מוריד ומתקין..." -ForegroundColor Yellow
    
    # נסה winget
    Write-Host "  מנסה winget..." -ForegroundColor Gray
    try {
        & winget install Python.Python.3.11 -e --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
    } catch {}
    
    # רענן PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    Start-Sleep -Seconds 2
    
    # בדוק שוב
    try {
        $pyVer = & python --version 2>&1
        if ($pyVer -match "Python") { $pythonCmd = "python" }
    } catch {}
    
    if (-not $pythonCmd) {
        try {
            $pyVer = & py -3 --version 2>&1
            if ($pyVer -match "Python") { $pythonCmd = "py -3" }
        } catch {}
    }
    
    if (-not $pythonCmd) {
        # הורדה ישירה
        Write-Host "  winget נכשל, מוריד ישירות..." -ForegroundColor Gray
        $pyInstaller = "$env:TEMP\python-installer.exe"
        try {
            Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" -OutFile $pyInstaller -UseBasicParsing
            Write-Host "  מתקין Python..." -ForegroundColor Gray
            Start-Process -FilePath $pyInstaller -ArgumentList "/passive","InstallAllUsers=1","PrependPath=1" -Wait
            Remove-Item $pyInstaller -ErrorAction SilentlyContinue
            
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            Start-Sleep -Seconds 2
            
            try { $pyVer = & python --version 2>&1; if ($pyVer -match "Python") { $pythonCmd = "python" } } catch {}
            if (-not $pythonCmd) { try { $pyVer = & py -3 --version 2>&1; if ($pyVer -match "Python") { $pythonCmd = "py -3" } } catch {} }
        } catch {
            Write-Host "  שגיאה בהורדת Python" -ForegroundColor Red
        }
    }
}

if (-not $pythonCmd) {
    Write-Host ""
    Write-Host "נכשלה התקנת Python!" -ForegroundColor Red
    Write-Host "נא להתקין Python ידנית מ: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "סמן 'Add Python to PATH' במהלך ההתקנה!" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "לחץ ENTER לסגירה"
    exit 1
}

Write-Host "  Python: $pythonCmd" -ForegroundColor Green
Write-Host ""

# ═══ בדיקת Git ═══
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
    try {
        & winget install Git.Git -e --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Write-Host "  Git הותקן" -ForegroundColor Green
    } catch {
        Write-Host "  נא להתקין Git מ https://git-scm.com" -ForegroundColor Red
    }
}
Write-Host ""

# ═══ הורדת והרצת המתקין ═══
Write-Host "[3/3] מוריד ומריץ מתקין..." -ForegroundColor Cyan

$installerUrl = "https://raw.githubusercontent.com/sunraz/ShimiStudio/main/install_shimistudio.py"
$installerPath = "$INSTALL_DIR\install_shimistudio.py"

try {
    Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing
    Write-Host "  מתקין הורד" -ForegroundColor Green
} catch {
    Write-Host "  נכשלה הורדה מ GitHub" -ForegroundColor Red
    Read-Host "לחץ ENTER לסגירה"
    exit 1
}

Write-Host "  מריץ מתקין..." -ForegroundColor Green
Write-Host ""

# הרץ עם הפקודה שמצאנו (python, py -3, או נתיב מלא)
if ($pythonCmd -eq "py -3") {
    & py -3 $installerPath
} else {
    & $pythonCmd $installerPath
}

$exitCode = $LASTEXITCODE
if ($exitCode -ne 0 -and $exitCode -ne $null) {
    Write-Host ""
    Write-Host "המתקין נתקל בשגיאה. קוד: $exitCode" -ForegroundColor Yellow
}

Write-Host ""
Read-Host "לחץ ENTER לסגירה"
