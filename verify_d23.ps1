[CmdletBinding()]
param(
    [int]$Days = 30,
    [int]$Seed = 42
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$PythonCommand = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCommand = "py"
}
elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCommand = "python"
}
else {
    throw "Python 3.10+ was not found. Install Python and reopen PowerShell."
}

$LogDirectory = Join-Path $ProjectRoot "local_acceptance"
New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null

function Invoke-Gate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    & $PythonCommand @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE."
    }
}

Invoke-Gate "Complete offline unit suite" @(
    "-m", "unittest", "discover", "-s", "tests", "-q"
)

Invoke-Gate "D.2.0 PersistentProject regression" @(
    "run_project_trials.py",
    "--days", "$Days",
    "--seed", "$Seed",
    "--log-file", (Join-Path $LogDirectory "d23_project_regression.txt")
)

Invoke-Gate "D.2.1 Hydrology regression" @(
    "run_hydrology_trials.py",
    "--days", "$Days",
    "--log-file", (Join-Path $LogDirectory "d23_hydrology_regression.txt")
)

Invoke-Gate "D.2.2 Affordance regression" @(
    "run_affordance_trials.py",
    "--days", "$Days",
    "--log-file", (Join-Path $LogDirectory "d23_affordance_regression.txt")
)

Invoke-Gate "D.2.3 Aqueous Silver Echo acceptance" @(
    "run_aqueous_echo_trials.py",
    "--days", "$Days",
    "--seed", "$Seed",
    "--log-file", (Join-Path $LogDirectory "d23_aqueous_echo_acceptance.txt")
)

Write-Host ""
Write-Host "All D.2.3 commands exited successfully." -ForegroundColor Green
Write-Host "Expected summaries: 139 tests; LAW 10/10, 19/19, 26/26, 26/26."
Write-Host "Review the printed totals before marking D.2.3 user-local accepted."
Write-Host "Local logs: $LogDirectory"
