# 智能通用网页嗅探与抓取系统 (商业级架构)

## 目录结构
- `main_ui.py`: PyQt5 桌面主程序界面（网址输入、类型勾选树、资源列表表格、进度条、实时日志）
- `sniffer_magic.py`: 二进制文件指纹（Magic Number）识别，**穿透网站扩展名伪装**（即使把 mp4 伪装为 png，或把 pdf 伪装为 dat 也能识别）
- `sniffer_engine.py`: 深度网络与 DOM 嗅探引擎，支持静态 DOM 解析、内联 JS 媒体提取、MIME 探测，并预留 Playwright CDP 网络层拦截
- `downloader.py`: 下载引擎，支持防盗链（Referer 穿透）、大文件分块流式写入、自动唤起内嵌 FFmpeg 将 m3u8 流切片无损合并转码为 mp4
- `build_exe.py`: 一键打包为 Windows `.exe` 的打包脚本

## 本地启动与测试
```bash
python3 main_ui.py
```

## 打包为 Windows .exe
在 Windows 电脑上进入该目录运行：
```bash
python build_exe.py
```
打包生成的可执行程序位于 `dist/UniversalResourceScraper/UniversalResourceScraper.exe`。
