# 万能钥匙 (UniversalKey) - Windows 客户端打包与安装向导制作指南

本项目支持生成两种 Windows 交付形态：
1. **像《英雄联盟》LOL一样的安装包向导**（`万能钥匙_极速安装向导.exe`，带安装步骤、快捷方式、控制面板卸载）；
2. **绿色免安装单文件版**（`万能钥匙_便携版.exe`，单个独立文件，双击直接运行）。

---

## 方式一：在 Windows 电脑上一键全自动打包（推荐）

把当前项目文件夹（`universal_scraper`）拷贝到任何一台 Windows 电脑或虚拟机上：

1. **双击运行 `build_for_windows.bat`**：
   * 脚本会自动配置 Python 环境依赖；
   * 自动使用 PyInstaller 将代码、资源、PyQt5、WebEngine 微内核与流媒体引擎打包到 `dist\万能钥匙\`。
2. **生成安装向导（Installer）**：
   * 在 Windows 电脑上安装免费的 [Inno Setup 6](https://jrsoftware.org/isdl.php)；
   * 右键本目录下的 `build_windows_installer.iss`，选择 **Compile**；
   * 几秒钟后，即可在 `installer_output\` 文件夹下得到：
     > `万能钥匙_极速安装向导_v2.0.0.exe`
3. **交付给同事**：
   * 把这个安装向导发给同事，同事双击后弹出像 LOL 一样的安装窗口，点击“下一步”安装完成，桌面自动生成图标，开箱即用！

---

## 方式二：生成单文件绿色版（无需安装向导）

如果想省去安装步骤，直接给同事一个单个的 `.exe` 文件：
* 在 Windows 机器上双击运行 `build_for_windows_onefile.bat`；
* 构建完成后，直接把 `dist\万能钥匙_便携版.exe` 发给同事即可。
