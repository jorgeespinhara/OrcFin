# Creates/updates the OrcFin desktop shortcut.
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\create_desktop_shortcut.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\create_desktop_shortcut.ps1 -Mode Dev
#   powershell -ExecutionPolicy Bypass -File scripts\create_desktop_shortcut.ps1 -Mode Product
#   powershell -ExecutionPolicy Bypass -File scripts\create_desktop_shortcut.ps1 -ExePath "C:\Programas\OrcFin\OrcFin.exe"
#
# Modes:
#   Auto    - prefer OrcFin.exe (dist/portable); else Dev (pythonw + main.py)
#   Product - require an .exe (dist or -ExePath)
#   Dev     - pythonw + main.py in the repo

param(
    [ValidateSet("Auto", "Product", "Dev")]
    [string]$Mode = "Auto",
    [string]$ExePath = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = (Split-Path $PSScriptRoot -Parent | Resolve-Path).Path
$mainPy = Join-Path $projectRoot "main.py"
$iconPath = Join-Path $projectRoot "assets\orcfin.ico"

function Find-ProductExe {
    param([string]$Root, [string]$Explicit)
    if ($Explicit) {
        if (-not (Test-Path -LiteralPath $Explicit)) {
            throw "ExePath not found: $Explicit"
        }
        return (Resolve-Path -LiteralPath $Explicit).Path
    }
    $candidates = @(
        (Join-Path $Root "dist\OrcFin-portable\OrcFin.exe"),
        (Join-Path $Root "dist\OrcFin\OrcFin.exe")
    )
    foreach ($c in $candidates) {
        if (Test-Path -LiteralPath $c) {
            return (Resolve-Path -LiteralPath $c).Path
        }
    }
    return $null
}

function Find-PythonW {
    $pythonwCmd = Get-Command pythonw -ErrorAction SilentlyContinue
    if ($pythonwCmd) { return $pythonwCmd.Source }
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $candidate = Join-Path (Split-Path $pythonCmd.Source -Parent) "pythonw.exe"
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    return $null
}

function Resolve-DesktopPath {
    $desktop = [Environment]::GetFolderPath("Desktop")
    if ($desktop -and (Test-Path -LiteralPath $desktop)) { return $desktop }

    $fallbacks = @(
        (Join-Path $env:USERPROFILE "OneDrive\Desktop"),
        (Join-Path $env:USERPROFILE "Desktop")
    )
    # Portuguese Windows / OneDrive localized name
    $ptDesktop = Join-Path $env:USERPROFILE "OneDrive\Area de Trabalho"
    $fallbacks = @($ptDesktop) + $fallbacks
    foreach ($fb in $fallbacks) {
        if (Test-Path -LiteralPath $fb) { return $fb }
    }
    throw "Desktop folder not found."
}

$targetPath = $null
$arguments = ""
$workingDir = $projectRoot

# Prefer assets\orcfin.ico (transparent squircle). Using the .exe as icon source
# only helps after a rebuild that embeds the updated ICO.
function Resolve-IconLocation {
    param([string]$Exe, [string]$Ico)
    if ($Ico -and (Test-Path -LiteralPath $Ico)) {
        return "$Ico,0"
    }
    if ($Exe -and (Test-Path -LiteralPath $Exe)) {
        return "$Exe,0"
    }
    return $null
}

$productExe = Find-ProductExe -Root $projectRoot -Explicit $ExePath
if ($Mode -eq "Product") {
    if (-not $productExe) {
        throw "Product mode: OrcFin.exe not found. Run package_portable.py or pass -ExePath."
    }
    $targetPath = $productExe
    $workingDir = Split-Path $productExe -Parent
} elseif ($Mode -eq "Dev") {
    if (-not (Test-Path -LiteralPath $mainPy)) {
        throw "main.py not found at: $projectRoot"
    }
    $pythonw = Find-PythonW
    if (-not $pythonw) {
        throw "pythonw.exe not found in PATH. Install Python 3.11+ or use -Mode Product."
    }
    $targetPath = $pythonw
    $arguments = "`"$mainPy`""
    $workingDir = $projectRoot
} else {
    # Auto
    if ($productExe) {
        $targetPath = $productExe
        $workingDir = Split-Path $productExe -Parent
    } else {
        if (-not (Test-Path -LiteralPath $mainPy)) {
            throw "main.py not found at: $projectRoot"
        }
        $pythonw = Find-PythonW
        if (-not $pythonw) {
            throw "Neither OrcFin.exe nor pythonw.exe found. Package the app or install Python 3.11+."
        }
        $targetPath = $pythonw
        $arguments = "`"$mainPy`""
        $workingDir = $projectRoot
    }
}

$iconLocation = Resolve-IconLocation -Exe $productExe -Ico $iconPath

$desktop = Resolve-DesktopPath
$shortcutPath = Join-Path $desktop "OrcFin.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetPath
$shortcut.Arguments = $arguments
$shortcut.WorkingDirectory = $workingDir
if ($iconLocation) {
    $shortcut.IconLocation = $iconLocation
}
$shortcut.Description = "OrcFin - Orcamento Financeiro"
$shortcut.Save()

Write-Host "Shortcut updated: $shortcutPath"
Write-Host "Target:           $targetPath $arguments"
Write-Host "Working dir:      $workingDir"
if ($iconLocation) {
    Write-Host "Icon:             $iconLocation"
} else {
    Write-Host "Icon:             (Windows default - assets\orcfin.ico missing)"
}
Write-Host "Project:          $projectRoot"
