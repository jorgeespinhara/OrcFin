$projectRoot = (Split-Path $PSScriptRoot -Parent | Resolve-Path).Path
$mainPy = Join-Path $projectRoot "main.py"
$iconPath = Join-Path $projectRoot "assets\orcfin.ico"

if (-not (Test-Path $mainPy)) {
    throw "main.py não encontrado em: $projectRoot"
}

$pythonwCmd = Get-Command pythonw -ErrorAction SilentlyContinue
$pythonw = if ($pythonwCmd) { $pythonwCmd.Source } else { $null }
if (-not $pythonw) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $pythonw = Join-Path (Split-Path $pythonCmd.Source -Parent) "pythonw.exe"
    }
}
if (-not $pythonw -or -not (Test-Path $pythonw)) {
    throw "pythonw.exe não encontrado no PATH. Instale Python 3.11+ e tente novamente."
}

$desktop = [Environment]::GetFolderPath("Desktop")
if (-not (Test-Path $desktop)) {
    $desktop = Join-Path $env:USERPROFILE "OneDrive\Área de Trabalho"
}

$shortcutPath = Join-Path $desktop "OrcFin.lnk"
$legacyShortcut = Join-Path $desktop "FinForge.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = "`"$mainPy`""
$shortcut.WorkingDirectory = $projectRoot
if (Test-Path $iconPath) {
    $shortcut.IconLocation = "$iconPath,0"
}
$shortcut.Description = "OrcFin - Orçamento Financeiro"
$shortcut.Save()

if (Test-Path $legacyShortcut) {
    Remove-Item $legacyShortcut -Force
}

Write-Host "Atalho criado: $shortcutPath"
Write-Host "Pasta do projeto: $projectRoot"