# Build VoxNote desktop bundle on Windows.
# Usage:  powershell -ExecutionPolicy Bypass -File apps/voxnote/packaging/build.ps1
#
# Steps:
#   1. pyinstaller --onedir  ->  dist/voxnote/voxnote.exe + ui/
#   2. (optional) ISCC.exe   ->  dist/voxnote-<ver>-windows-x64-setup.exe
#   3. Compress-Archive      ->  dist/voxnote-<ver>-windows-x64.zip (always)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot/../../..").Path
$env:VOXNOTE_ROOT = $root

Write-Host "[voxnote] root = $root"
Push-Location $root
try {
    python -m pip install --upgrade pip
    pip install -e .
    pip install -e "apps/voxnote[build,windows]"
    pyinstaller --noconfirm "apps/voxnote/packaging/voxnote.spec"

    $stage = "dist/voxnote"
    if (-not (Test-Path $stage)) { throw "PyInstaller output not found at $stage" }

    $version = (python -c "import apps.voxnote.voxnote as m; print(m.__version__)")

    # --- Always produce a portable zip ---
    $zip = "dist/voxnote-$version-windows-x64.zip"
    if (Test-Path $zip) { Remove-Item $zip }
    Compress-Archive -Path "$stage/*" -DestinationPath $zip
    Write-Host "[voxnote] portable bundle: $zip"

    # --- Optional: Inno Setup installer ---
    $iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path $iscc) {
        & $iscc "apps/voxnote/packaging/installer.iss"
        Write-Host "[voxnote] installer ready (see dist\voxnote-$version-windows-x64-setup.exe)"
    } else {
        Write-Host "[voxnote] Inno Setup not found at '$iscc' — skipping installer."
    }
} finally {
    Pop-Location
}
