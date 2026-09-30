<#
.SYNOPSIS
  Reprodukovatelny Windows ONE-DIR build: dist/Seznamy/Seznamy.exe
.DESCRIPTION
  1. Smaze stare build/ a dist/ (pouze build vystup, zdrojaku se nedotyka).
  2. Pripravi ciste venv .venv-build.
  3. Nainstaluje requirements.txt + requirements-build.txt.
  4. Zjisti git commit + cas, vygeneruje _build_info.py.
  5. Spusti PyInstaller (Seznamy.spec, one-dir, console=False).
  6. Smoke kontrola: existence EXE + pytest startup smoke v build venv.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $RepoRoot

Write-Host "=== 1/6 cistim build/ dist/ ==="
foreach ($d in @("build", "dist")) {
    if (Test-Path -LiteralPath $d) {
        Remove-Item -LiteralPath $d -Recurse -Force
    }
}

Write-Host "=== 2/6 venv .venv-build ==="
$VenvPython = Join-Path $RepoRoot ".venv-build\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) {
    & "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" -m venv .venv-build
}
& $VenvPython -m pip install --upgrade pip

Write-Host "=== 3/6 instaluji zavislosti ==="
& $VenvPython -m pip install -r requirements.txt -r requirements-build.txt

Write-Host "=== 4/6 generuji _build_info.py ==="
$Commit = (git rev-parse HEAD).Trim()
$BuildTime = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$BuildInfo = "# Generovano build.ps1 – necommitovat.`nBUILD_COMMIT = '$Commit'`nBUILD_TIME = '$BuildTime'`n"
Set-Content -LiteralPath (Join-Path $RepoRoot "_build_info.py") -Value $BuildInfo -Encoding UTF8

Write-Host "APP_VERSION + commit: $Commit ($BuildTime)"

Write-Host "=== 5/6 PyInstaller (one-dir) ==="
& (Join-Path $RepoRoot ".venv-build\Scripts\pyinstaller.exe") Seznamy.spec

Write-Host "=== 6/6 smoke kontrola ==="
$Exe = Join-Path $RepoRoot "dist\Seznamy\Seznamy.exe"
if (-not (Test-Path -LiteralPath $Exe)) {
    throw "Build selhal: $Exe neexistuje."
}
Write-Host "EXE existuje: $Exe"
& $VenvPython -m pytest tests/test_startup_smoke.py -q
Write-Host "Hotovo: $Exe (commit $Commit)"
