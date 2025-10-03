# PowerShell helper to run Synthea cohorts on Windows.
# Usage: pwsh ./scripts/run_synthea_cohorts.ps1 -SyntheaDir "C:\path\to\synthea" -OutRoot "..\..\data\synthea" -Populations @(100,1000,10000) -State "Massachusetts"

param(
    [Parameter(Mandatory=$true)][string]$SyntheaDir,
    [string]$OutRoot = "..\..\data\synthea",
    [int[]]$Populations = @(100),
    [string]$State = "Massachusetts"
)

$date = Get-Date -Format "yyyyMMdd-HHmm"
foreach ($p in $Populations) {
    $out = Join-Path $OutRoot "$date-$p"
    [void][System.IO.Directory]::CreateDirectory($out)
    $outFull = [System.IO.Path]::GetFullPath($out)
    Push-Location $SyntheaDir
    ./gradlew.bat build | Out-Null
    $env:SYNTHEA_OUTPUT = $outFull
    ./run_synthea.bat -p $p $State | Write-Output
    Pop-Location
}

Write-Output "Cohorts written under $OutRoot"


