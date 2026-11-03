; Compile: ISCC /DBundleDir=<absolute validated bundle> /DReleaseDir=<absolute output> RetailDataStudio.iss
#ifndef BundleDir
  #error BundleDir is required
#endif
#ifndef ReleaseDir
  #error ReleaseDir is required
#endif

[Setup]
AppId={{D843C614-03AC-49B0-A5F0-95F50880EB13}
AppName=Retail Data Studio
AppVersion=2.5
AppVerName=Retail Data Studio V2.5
VersionInfoVersion=2.5.0.0
AppPublisher=Retail Data Studio
DefaultDirName={localappdata}\Programs\RetailDataStudio
DefaultGroupName=Retail Data Studio
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#ReleaseDir}
OutputBaseFilename=RetailDataStudio-Setup-v2.5
SetupIconFile=..\src\assets\retail.ico
UninstallDisplayIcon={app}\RetailDataStudio.exe
Compression=lzma2/normal
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
AppMutex=Local\RetailDataStudio.Running
CloseApplications=no
RestartApplications=no
Uninstallable=yes
CreateUninstallRegKey=yes
UninstallDisplayName=Retail Data Studio
InfoAfterFile=INSTALLATION_NOTES.txt

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Retail Data Studio"; Filename: "{app}\RetailDataStudio.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\Retail Data Studio"; Filename: "{app}\RetailDataStudio.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\RetailDataStudio.exe"; Description: "{cm:LaunchProgram,Retail Data Studio}"; Flags: nowait postinstall skipifsilent

; Remove only obsolete bundled Qt components during a Matplotlib upgrade.
; Never target project/user data or recursively delete directories.
[InstallDelete]
Type: files; Name: "{app}\_internal\PySide6\Qt6Charts.dll"
Type: files; Name: "{app}\_internal\PySide6\Qt6Pdf.dll"
Type: files; Name: "{app}\_internal\PySide6\Qt6Qml.dll"
Type: files; Name: "{app}\_internal\PySide6\Qt6QmlMeta.dll"
Type: files; Name: "{app}\_internal\PySide6\Qt6QmlModels.dll"
Type: files; Name: "{app}\_internal\PySide6\Qt6QmlWorkerScript.dll"
Type: files; Name: "{app}\_internal\PySide6\Qt6Quick.dll"
Type: files; Name: "{app}\_internal\PySide6\Qt6VirtualKeyboard.dll"
Type: files; Name: "{app}\_internal\PySide6\QtCharts.pyd"
Type: files; Name: "{app}\_internal\PySide6\plugins\imageformats\qpdf.dll"
Type: files; Name: "{app}\_internal\PySide6\plugins\platforminputcontexts\qtvirtualkeyboardplugin.dll"

; No UninstallDelete, user-data copy, migration or reset.
[Code]
function NextButtonClick(CurPageID: Integer): Boolean;
var
  Target, DataRoot: String;
begin
  Result := True;
  if CurPageID = wpSelectDir then begin
    Target := AddBackslash(Lowercase(ExpandFileName(WizardDirValue)));
    DataRoot := AddBackslash(Lowercase(ExpandConstant('{localappdata}\RetailDataStudio')));
    if (Pos(DataRoot, Target) = 1) or (Pos(Target, DataRoot) = 1) then begin
      MsgBox('Program files must be installed separately from Retail Data Studio user data.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Target, DataRoot: String;
begin
  Result := '';
  Target := AddBackslash(Lowercase(ExpandFileName(ExpandConstant('{app}'))));
  DataRoot := AddBackslash(Lowercase(ExpandConstant('{localappdata}\RetailDataStudio')));
  if (Pos(DataRoot, Target) = 1) or (Pos(Target, DataRoot) = 1) then
    Result := 'Installation directory overlaps the protected user-data directory.';
end;
