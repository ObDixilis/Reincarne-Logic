[CmdletBinding()]
param([int]$Port = 8765, [string]$PythonPath)
$ErrorActionPreference = 'Stop'
if (-not $PythonPath) {
    $bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundledPython) {
        $PythonPath = $bundledPython
    } else {
        $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if (-not $pythonCommand) { throw 'Python 3.10+ is required. Supply -PythonPath with its executable.' }
        $PythonPath = $pythonCommand.Source
    }
}
Write-Host 'Opening Star Weaver. Keep this window open; close it to stop the local workbench.'
& $PythonPath -B (Join-Path $PSScriptRoot 'server.py') --port $Port --open
exit $LASTEXITCODE
