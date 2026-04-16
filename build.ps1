<#
.SYNOPSIS
    AirType build script using Astral uv.

.DESCRIPTION
    Automates the entire lifecycle: venv creation, dependency installation
    (including CUDA torch), and PyInstaller bundling into a standalone .exe.

.PARAMETER Clean
    Remove previous build artifacts before building.

.PARAMETER NoExe
    Only set up the environment without building the exe.

.PARAMETER CudaVersion
    CUDA toolkit version for PyTorch. Default: "12.6".
    Common values: "12.6", "12.4", "12.1".

.EXAMPLE
    .\build.ps1 -Clean
    .\build.ps1 -CudaVersion "12.4"
    .\build.ps1 -NoExe
#>

param(
    [switch]$Clean,
    [switch]$NoExe,
    [string]$CudaVersion = "12.6"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$TorchIndexUrl = "https://download.pytorch.org/whl/cu$($CudaVersion -replace '\.','')"

Write-Host "`n=== AirType Build Script ===" -ForegroundColor Cyan
Write-Host "  CUDA version : $CudaVersion"
Write-Host "  Torch index  : $TorchIndexUrl`n"

# --- Clean ---
if ($Clean) {
    Write-Host "[clean] Removing previous builds..." -ForegroundColor Yellow
    @(".venv", "build", "dist") | ForEach-Object {
        $path = Join-Path $ProjectRoot $_
        if (Test-Path $path) {
            Remove-Item -Recurse -Force $path
            Write-Host "  Removed $_"
        }
    }
}

# --- Virtual Environment ---
Write-Host "[1/4] Creating virtual environment..." -ForegroundColor Yellow
uv venv (Join-Path $ProjectRoot ".venv")
if ($LASTEXITCODE -ne 0) { throw "Failed to create venv" }

# --- CUDA PyTorch ---
Write-Host "[2/4] Installing PyTorch (CUDA $CudaVersion)..." -ForegroundColor Yellow
uv pip install `
    "torch>=2.5" `
    "torchaudio>=2.5" `
    "--index-url" $TorchIndexUrl `
    "--python" $PythonExe
if ($LASTEXITCODE -ne 0) { throw "Failed to install PyTorch CUDA" }

# Verify CUDA is available
Write-Host "  Verifying CUDA..." -ForegroundColor DarkGray
& $PythonExe -c "import torch; print(f'  torch {torch.__version__}  CUDA available: {torch.cuda.is_available()}')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "  WARNING: CUDA check failed. GPU may not be available." -ForegroundColor Red
}

# --- Application Dependencies ---
Write-Host "[3/4] Installing application dependencies..." -ForegroundColor Yellow
uv pip install -e $ProjectRoot --python $PythonExe
if ($LASTEXITCODE -ne 0) { throw "Failed to install dependencies" }

# Install qwen_asr from PyPI
Write-Host "  Installing qwen_asr..." -ForegroundColor DarkGray
uv pip install "qwen-asr" --python $PythonExe
if ($LASTEXITCODE -ne 0) {
    Write-Host "  qwen-asr not on PyPI, trying GitHub..." -ForegroundColor DarkGray
    uv pip install "git+https://github.com/QwenLM/Qwen3-ASR" --python $PythonExe
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  WARNING: Could not install qwen_asr. Install manually." -ForegroundColor Red
    }
}

# Install PyInstaller (dev dependency)
uv pip install pyinstaller --python $PythonExe

if ($NoExe) {
    Write-Host "`nEnvironment ready. Skipping exe build." -ForegroundColor Green
    exit 0
}

# --- Build Executable ---
Write-Host "[4/4] Building standalone .exe with PyInstaller..." -ForegroundColor Yellow

$mainScript = Join-Path $ProjectRoot "airtype\main.py"
$iconPath = Join-Path $ProjectRoot "assets\icon.ico"

$pyinstallerArgs = @(
    "--name", "AirType",
    "--noconfirm",
    "--windowed",
    "--clean",
    "--collect-all", "torch",
    "--collect-all", "torchaudio",
    "--collect-all", "transformers",
    "--collect-all", "accelerate",
    "--hidden-import", "sounddevice",
    "--hidden-import", "keyboard",
    "--hidden-import", "pyautogui",
    "--hidden-import", "win32mica",
    "--hidden-import", "openai",
    "--hidden-import", "qwen_asr"
)

if (Test-Path $iconPath) {
    $pyinstallerArgs += @("--icon", $iconPath)
}

$pyinstallerArgs += $mainScript

& $PythonExe -m PyInstaller @pyinstallerArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }

Write-Host "`n=== Build complete ===" -ForegroundColor Green
Write-Host "Output: $(Join-Path $ProjectRoot 'dist\AirType.exe')" -ForegroundColor Green
