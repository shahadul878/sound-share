; SoundShare Windows Installer
; Developer: H M Shahadul Islam

#define MyAppName "SoundShare"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "H M Shahadul Islam"
#define MyAppURL "https://github.com/"
#define MyAppExeName "SoundShare.exe"

[Setup]
AppId={{A7B3C9D1-8E2F-4A5B-9C6D-1E2F3A4B5C6D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=SoundShare-Setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\installer\LICENSE.txt
InfoBeforeFile=..\installer\WELCOME.txt
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce
Name: "firewall"; Description: "Allow SoundShare through Windows Firewall (port 8765)"; GroupDescription: "Network:"; Flags: checkedonce

[Files]
; VB-Audio Virtual Cable (bundled)
Source: "..\vendor\VBCABLE_Setup_x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: VbcableNeeded
; SoundShare application
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\installer\ABOUT.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\About SoundShare"; Filename: "notepad.exe"; Parameters: """{app}\ABOUT.txt"""
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; WorkingDir: "{app}"

[Run]
; Silent install VB-Audio Virtual Cable
Filename: "{tmp}\VBCABLE_Setup_x64.exe"; Parameters: "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-"; StatusMsg: "Installing virtual audio driver..."; Flags: waituntilterminated; Check: VbcableNeeded
; Windows Firewall rule
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""SoundShare"" dir=in action=allow protocol=TCP localport=8765"; Flags: runhidden; Tasks: firewall; StatusMsg: "Configuring firewall..."
; Launch after install
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""SoundShare"""; Flags: runhidden; Tasks: firewall

[Code]
function VbcableInstalled: Boolean;
var
  ResultCode: Integer;
begin
  Result := RegKeyExists(HKLM, 'SOFTWARE\VB-Audio\Cable');
  if not Result then
    Result := RegKeyExists(HKLM, 'SOFTWARE\WOW6432Node\VB-Audio\Cable');
end;

function VbcableNeeded: Boolean;
begin
  Result := not VbcableInstalled;
end;

function InitializeSetup: Boolean;
begin
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    { VB-Cable installed; SoundShare will configure virtual speaker on first run }
  end;
end;

[Messages]
WelcomeLabel2=This will install [name/ver] on your computer.%n%nSoundShare streams PC audio to phones and tablets on your network. The installer includes the VB-Audio Virtual Cable driver — no extra setup required.%n%nDeveloped by H M Shahadul Islam.
