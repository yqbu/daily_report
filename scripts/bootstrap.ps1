<#
.SYNOPSIS
    Bootstrap script for the Daily Report project on Windows.

.DESCRIPTION
    This script creates a clean virtual environment, installs the project
    from pyproject.toml, and verifies that the FastAPI application can be imported.

    Recommended usage:
        .\scripts\bootstrap.ps1

    Install with dev dependencies:
        .\scripts\bootstrap.ps1 -Dev

    Recreate .venv from scratch:
        .\scripts\bootstrap.ps1 -Force

    Specify a Python executable explicitly:
        .\scripts\bootstrap.ps1 -PythonExecutable "D:\Users\00807909\AppData\Local\Programs\Python\Python312\python.exe"

.NOTES
    Recommended Python:
        python.org Python 3.11 / 3.12 x64

    Not recommended:
        Microsoft WindowsApps python.exe placeholder
        Python versions outside the range declared in pyproject.toml
#>

param(
    # Install optional dev dependencies: python -m pip install -e ".[dev]"
    [switch]$Dev,

    # Remove and recreate the virtual environment even if it already exists.
    [switch]$Force,

    # Skip the application import smoke test.
    [switch]$NoTest,

    # Install project in non-editable mode: python -m pip install .
    [switch]$NoEditable,

    # Allow conda Python when explicitly requested.
    [switch]$AllowConda,

    # Explicit Python executable path. This has the highest priority.
    [string]$PythonExecutable = "",

    # Virtual environment directory name or path.
    [string]$VenvDir = ".venv"
)

$ErrorActionPreference = "Stop"

# -----------------------------------------------------------------------------
# Console encoding
# -----------------------------------------------------------------------------
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    # Ignore encoding setup failure in restricted hosts.
}

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "[ OK ] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Resolve-ProjectRoot {
    $scriptDir = Split-Path -Parent $PSCommandPath

    $candidates = @(
        $scriptDir,
        (Join-Path $scriptDir ".."),
        (Get-Location).Path
    )

    foreach ($candidate in $candidates) {
        $resolved = Resolve-Path $candidate -ErrorAction SilentlyContinue
        if ($null -ne $resolved) {
            $path = $resolved.Path
            if (Test-Path (Join-Path $path "pyproject.toml")) {
                return $path
            }
        }
    }

    throw "Cannot find pyproject.toml. Please run this script from the project root or place it under scripts/."
}

function Test-WindowsAppsPython {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $false
    }
    return $Path.ToLowerInvariant().Contains("\microsoft\windowsapps\python")
}

function Test-CondaPython {
    param([string]$PythonPath)

    try {
        $result = & $PythonPath -c "import sys, os; s=(sys.version + ' ' + sys.executable + ' ' + os.environ.get('CONDA_PREFIX','')).lower(); print('true' if 'conda' in s else 'false')"
        return ($result.Trim().ToLowerInvariant() -eq "true")
    } catch {
        return $false
    }
}

function Get-PythonVersionInfo {
    param([string]$PythonPath)

    $json = & $PythonPath -c "import sys, json, struct; print(json.dumps({'major':sys.version_info.major,'minor':sys.version_info.minor,'micro':sys.version_info.micro,'executable':sys.executable,'version':sys.version,'bits':struct.calcsize('P')*8}, ensure_ascii=False))"
    return $json | ConvertFrom-Json
}

function Test-PythonUsable {
    param(
        [string]$PythonPath,
        [bool]$AllowCondaPython
    )

    if ([string]::IsNullOrWhiteSpace($PythonPath)) {
        return $false
    }

    if (!(Test-Path $PythonPath)) {
        return $false
    }

    if (Test-WindowsAppsPython $PythonPath) {
        Write-Warn "Skip WindowsApps placeholder: $PythonPath"
        return $false
    }

    try {
        $info = Get-PythonVersionInfo $PythonPath
    } catch {
        Write-Warn "Skip unusable Python: $PythonPath"
        return $false
    }

    if ($info.major -ne 3 -or ($info.minor -lt 11 -or $info.minor -gt 12)) {
        Write-Warn "Skip Python $($info.major).$($info.minor).$($info.micro): $PythonPath. Recommended: Python 3.11 or 3.12."
        return $false
    }

    if ($info.bits -ne 64) {
        Write-Warn "Skip non-64-bit Python: $PythonPath"
        return $false
    }

    $isConda = Test-CondaPython $PythonPath
    if ($isConda -and !$AllowCondaPython) {
        Write-Warn "Skip conda Python: $PythonPath. Use -AllowConda if you intentionally want it."
        return $false
    }

    return $true
}

function Find-PythonExecutable {
    param(
        [string]$ExplicitPython,
        [bool]$AllowCondaPython
    )

    $candidates = New-Object System.Collections.Generic.List[string]

    if (![string]::IsNullOrWhiteSpace($ExplicitPython)) {
        $candidates.Add($ExplicitPython)
    }

    # Common python.org installation paths for the current user.
    $localAppData = $env:LOCALAPPDATA
    if (![string]::IsNullOrWhiteSpace($localAppData)) {
        $candidates.Add((Join-Path $localAppData "Programs\Python\Python312\python.exe"))
        $candidates.Add((Join-Path $localAppData "Programs\Python\Python311\python.exe"))
    }


    # Try py launcher if available.
    $pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($null -ne $pyLauncher) {
        foreach ($version in @("3.12", "3.11")) {
            try {
                $path = & py -$version -c "import sys; print(sys.executable)" 2>$null
                if (![string]::IsNullOrWhiteSpace($path)) {
                    $candidates.Add($path.Trim())
                }
            } catch {
                # Ignore unavailable py launcher versions.
            }
        }
    }

    # Try python commands on PATH. This may include WindowsApps; it will be filtered.
    foreach ($commandName in @("python.exe", "python3.exe")) {
        $commands = Get-Command $commandName -All -ErrorAction SilentlyContinue
        foreach ($cmd in $commands) {
            if ($null -ne $cmd.Source) {
                $candidates.Add($cmd.Source)
            }
        }
    }

    $uniqueCandidates = $candidates | Where-Object { ![string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique

    Write-Info "Searching for a suitable Python executable..."
    foreach ($candidate in $uniqueCandidates) {
        Write-Info "Check Python candidate: $candidate"
        if (Test-PythonUsable -PythonPath $candidate -AllowCondaPython $AllowCondaPython) {
            return (Resolve-Path $candidate).Path
        }
    }

    throw @"
No suitable Python executable found.

Please install python.org Python 3.12 x64, then rerun this script.
Recommended install command:
    winget install -e --id Python.Python.3.12

If python is already installed, pass it explicitly:
    .\scripts\bootstrap.ps1 -PythonExecutable "D:\Users\00807909\AppData\Local\Programs\Python\Python312\python.exe"
"@
}

function Invoke-Step {
    param(
        [string]$Title,
        [scriptblock]$ScriptBlock
    )

    Write-Info $Title
    & $ScriptBlock
    Write-Ok $Title
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
try {
    $projectRoot = Resolve-ProjectRoot
    Set-Location $projectRoot
    Write-Info "Project root: $projectRoot"

    if (!(Test-Path (Join-Path $projectRoot "pyproject.toml"))) {
        throw "pyproject.toml does not exist under project root: $projectRoot"
    }

    $python = Find-PythonExecutable -ExplicitPython $PythonExecutable -AllowCondaPython ([bool]$AllowConda)
    $pythonInfo = Get-PythonVersionInfo $python
    Write-Ok "Selected Python: $($pythonInfo.executable)"
    Write-Ok "Python version: $($pythonInfo.version)"

    $venvPath = Join-Path $projectRoot $VenvDir

    if ((Test-Path $venvPath) -and $Force) {
        Invoke-Step "Removing existing virtual environment: $venvPath" {
            Remove-Item -Recurse -Force $venvPath
        }
    }

    if (!(Test-Path $venvPath)) {
        Invoke-Step "Creating virtual environment: $venvPath" {
            & $python -m venv $venvPath
        }
    } else {
        Write-Ok "Virtual environment already exists: $venvPath"
    }

    $venvPython = Join-Path $venvPath "Scripts\python.exe"
    if (!(Test-Path $venvPython)) {
        throw "Virtual environment python.exe not found: $venvPython"
    }

    $venvInfo = Get-PythonVersionInfo $venvPython
    Write-Ok "Venv Python: $($venvInfo.executable)"
    Write-Ok "Venv version: $($venvInfo.version)"

    if ($venvInfo.major -ne 3 -or ($venvInfo.minor -lt 11 -or $venvInfo.minor -gt 12)) {
        throw "The virtual environment Python version is $($venvInfo.major).$($venvInfo.minor). Please use Python 3.11 or 3.12."
    }

    Invoke-Step "Upgrading pip, setuptools, and wheel" {
        & $venvPython -m pip install -U pip setuptools wheel
    }

    if ($NoEditable) {
        $installTarget = "."
    } else {
        if ($Dev) {
            $installTarget = ".[dev]"
        } else {
            $installTarget = "."
        }
    }

    if ($NoEditable) {
        Invoke-Step "Installing project from pyproject.toml" {
            & $venvPython -m pip install $installTarget
        }
    } else {
        Invoke-Step "Installing project in editable mode from pyproject.toml" {
            & $venvPython -m pip install -e $installTarget
        }
    }

    if (!$NoTest) {
        Invoke-Step "Testing Daily Report API import" {
            & $venvPython -c "from daily_report.api.app import create_app; print(create_app().title)"
        }
    } else {
        Write-Warn "Skip application import test because -NoTest was specified."
    }

    Write-Host ""
    Write-Ok "Bootstrap completed successfully."
    Write-Host ""
    Write-Host "Next commands:" -ForegroundColor Cyan
    Write-Host "    .\$VenvDir\Scripts\Activate.ps1"
    Write-Host "    daily-report status --json"
    Write-Host "    daily-report gui"
    Write-Host ""
} catch {
    Write-Host ""
    Write-Fail $_.Exception.Message
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Recommended Python: python.org Python 3.12 x64"
    Write-Host "  2. Install command: winget install -e --id Python.Python.3.12"
    Write-Host "  3. If Python is installed but not detected, run:"
    Write-Host "       .\scripts\bootstrap.ps1 -PythonExecutable 'D:\Users\00807909\AppData\Local\Programs\Python\Python312\python.exe' -Force"
    Write-Host "  4. If PowerShell blocks script execution, run once:"
    Write-Host "       Set-ExecutionPolicy -Scope CurrentUser RemoteSigned"
    Write-Host ""
    exit 1
}
