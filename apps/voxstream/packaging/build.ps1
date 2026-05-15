# Build VoxStream desktop bundle on Windows.
# Usage: powershell -ExecutionPolicy Bypass -File apps/voxstream/packaging/build.ps1

$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot/../../..").Path
$env:VOXSTREAM_ROOT = $root

Write-Host "[voxstream] root = $root"
Push-Location $root
try {
    python -m pip install --upgrade pip
    pip install -e .
    pip install -e "apps/voxstream[build,windows]"
    pyinstaller --noconfirm "apps/voxstream/packaging/voxstream.spec"

    $stage = "dist/voxstream"
    if (-not (Test-Path $stage)) { throw "PyInstaller output not found at $stage" }

    $version = (python -c "import apps.voxstream.voxstream as m; print(m.__version__)")
    $zip = "dist/voxstream-$version-windows-x64.zip"
    if (Test-Path $zip) { Remove-Item $zip }
    Compress-Archive -Path "$stage/*" -DestinationPath $zip
    Write-Host "[voxstream] bundle ready: $zip"
} finally {
    Pop-Location
}
