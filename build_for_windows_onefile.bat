@echo off
chcp 65001 >nul
echo ========================================================
echo   万能钥匙 (UniversalKey) - 生成单文件绿色便携版 EXE
echo ========================================================
echo.

echo 正在构建独立单文件 EXE (所有依赖、UI与引擎均压入单个 .exe)...
pyinstaller --noconfirm --onefile --windowed ^
    --name="万能钥匙_便携版" ^
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
if exist "dist\万能钥匙_便携版.exe" (
    echo [完成] 独立的单文件 EXE 已生成在: dist\万能钥匙_便携版.exe
    echo 这个单个 exe 文件你可以直接发送给任何人，双击就能直接运行！
)
echo ========================================================
pause
