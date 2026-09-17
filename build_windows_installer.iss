; ========================================================
; OmniFinder (万象探索) - Windows 安装包制作脚本
; 基于 Inno Setup 6 构建
; ========================================================

#define MyAppName "OmniFinder"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "OmniFinder Community"
#define MyAppURL "https://github.com"
#define MyAppExeName "OmniFinder.exe"

[Setup]
; 基础应用信息
AppId={{8B1A2C3D-4E5F-6A7B-8C9D-0E1F2A3B4C5D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; 安装路径（默认安装在用户本地程序目录，无需管理员权限，安装极快）
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
DefaultGroupName={#MyAppName}

; 输出配置
OutputDir=installer_output
OutputBaseFilename=OmniFinder_安装向导_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes

; 界面视觉风格
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式 (&D)"; GroupDescription: "附加快捷选项:"; Flags: checkedonce

[Files]
; 打包后的整个目录文件全部打包进安装程序
Source: "dist\OmniFinder\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; 开始菜单与桌面图标配置
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载{#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; 安装完成后提示启动
Filename: "{app}\{#MyAppExeName}"; Description: "立即启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent
