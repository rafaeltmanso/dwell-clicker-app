; Dwell Clicker — Inno Setup Installer Script
; Build: iscc installer.iss

#define MyAppName "Dwell Clicker"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Rafael Manso"
#define MyAppURL "https://dwellclicker.com"
#define MyAppExeName "dwell-clicker-pro.exe"

[Setup]
AppId={{B8F4C3A1-2D5E-4F7A-9B1C-3E6D8A2F4C0B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=dist
OutputBaseFilename=dwell-clicker-setup-{#MyAppVersion}
SetupIconFile=app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"
Name: "startupicon"; Description: "Create a &Start Menu shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\dwell-clicker-pro.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "app.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\app.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Run Dwell Clicker"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/c ""REG DELETE HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v DwellClicker /f >nul 2>&1"""; Flags: runhidden

[Code]
function InitializeSetup: Boolean;
var
  ResultCode: Integer;
begin
  // Kill existing process before install
  ShellExec('open', 'taskkill', '/f /im dwell-clicker-pro.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;

[CustomMessages]
english.DwellClickerDescription = Automatically click when your cursor stops moving.
portuguese.DwellClickerDescription = Clique automaticamente quando o cursor fica parado.
