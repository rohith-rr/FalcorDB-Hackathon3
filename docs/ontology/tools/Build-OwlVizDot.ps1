param(
    [string] $GraphvizBin = (Join-Path $PSScriptRoot '../../../.local/tools/graphviz/Graphviz-16.1.0-win64/bin')
)

$ErrorActionPreference = 'Stop'
$GraphvizBin = (Resolve-Path -LiteralPath $GraphvizBin).Path
if (-not (Test-Path -LiteralPath (Join-Path $GraphvizBin 'dot.exe') -PathType Leaf)) {
    throw "dot.exe is missing from $GraphvizBin"
}

$launcherPath = Join-Path $GraphvizBin 'owlviz-dot.exe'
$temporaryAssembly = Join-Path $GraphvizBin ("owlviz-build-{0}.exe" -f [guid]::NewGuid().ToString('N'))
try {
    $source = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'OwlVizDot.cs') -Raw
    Add-Type -TypeDefinition $source -Language CSharp -OutputAssembly $temporaryAssembly -OutputType ConsoleApplication
    Copy-Item -LiteralPath $temporaryAssembly -Destination $launcherPath -Force
    Write-Output $launcherPath
}
finally {
    if (Test-Path -LiteralPath $temporaryAssembly) {
        Remove-Item -LiteralPath $temporaryAssembly -Force
    }
}
