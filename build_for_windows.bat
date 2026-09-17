@echo off
chcp 65001 >nul
echo ========================================================
echo   OmniFinder (万象探索) - Windows 一键全自动打包构建
echo ========================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python 环境！
    echo 请先安装 Python (建议 3.10-3.12) 并务必勾选 "Add Python to PATH"。
    pause
    exit /b
)

echo [第 1 步 / 共 3 步] 正在配置必要运行环境与依赖组件...
pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com pyinstaller PyQt5 PyQtWebEngine httpx beautifulsoup4 yt-dlp playwright requests

echo.
echo [第 2 步 / 共 3 步] 正在使用 PyInstaller 封装独立 Windows 应用程序...
pyinstaller --noconfirm --onedir --windowed ^
    --name="OmniFinder" ^
    --add-data="sniffer_magic.py;." ^
    --add-data="downloader.py;." ^
    --add-data="sniffer_engine.py;." ^
    --add-data="video_extractor.py;." ^
    --add-data="vip_parser.py;." ^
    --add-data="resource_searcher.py;." ^
    --add-data="player_server.py;." ^
    --add-data="i18n.py;." ^
    --add-data="assets;assets" ^
    main_ui.py

echo.
echo ========================================================
if exist "dist\OmniFinder\OmniFinder.exe" (
    echo [第 3 步 / 共 3 步] 应用程序已成功构建在:
    echo        dist\OmniFinder\OmniFinder.exe
    echo.
    echo --------------------------------------------------------
    echo 【直接交付方案】:
    echo  您可以直接把整个 "dist\OmniFinder" 文件夹压缩成 zip 发给同事，
    echo  同事解压后双击 "OmniFinder.exe" 即可直接使用（无需安装Python）！
    echo --------------------------------------------------------
) else (
    echo [打包失败] 请检查上方 Python / PyInstaller 报错信息。
)
echo ========================================================
pause
