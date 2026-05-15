; Inno Setup script for VoxNote (Windows installer).
;
; Usage:
;     1. Run PyInstaller first:  pyinstaller apps\voxnote\packaging\voxnote.spec
;     2. Then compile installer:  ISCC.exe apps\voxnote\packaging\installer.iss
;
; Output: dist\voxnote-{version}-windows-x64-setup.exe
;
; The installer registers a Start Menu shortcut, an optional Desktop icon, and
; a proper uninstaller in Add/Remove Programs.

#define AppName "VoxNote"
#define AppVersion "0.2.0"
#define AppPublisher "VoxCore"
#define AppURL "https://github.com/tianjimeteor/VoxCore"
#define AppExe "voxnote.exe"

[Setup]
AppId={{F2C7A8B3-9E44-4D11-8A6F-7E2C4D9B1A55}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
LicenseFile=..\..\..\LICENSE
OutputDir=..\..\..\dist
OutputBaseFilename=voxnote-{#AppVersion}-windows-x64-setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#AppExe}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinese"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; PyInstaller --onedir output: dist\voxnote\* (run from repo root, so relative
; path from this script is ..\..\..\dist\voxnote\*).
Source: "..\..\..\dist\voxnote\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
