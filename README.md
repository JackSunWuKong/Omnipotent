<div align="center">

# 🌟 OmniFinder (万象探索)
### 个人多媒体检索与网络协议技术探索工具 (学习研究版)
### Personal Web & Media Explorer for Research and Study

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![GUI Framework](https://img.shields.io/badge/GUI-PyQt5%20%7C%20QtWebEngine-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License](https://img.shields.io/badge/License-Academic%20Research%20Only-orange.svg)](#免责声明--legal-disclaimer)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey.svg)]()

[简体中文](#-简体中文) | [English Documentation](#-english-documentation)

</div>

---

# 🇨🇳 简体中文

## 📖 项目概述
**OmniFinder (万象探索)** 是一款专为**计算机网络协议分析、流媒体传输解码及多源信息聚合技术**研究而设计的开源桌面探索工具。

> [!NOTE]
> **合规声明**：本项目属于非商业性质的个人学术探索与技术实验项目，旨在研究客户端-服务端协议交互、流媒体切片合并技术与跨语言语义对齐算法。

---

## ✨ 核心特性

| 功能模块 | 技术实现 | 核心价值 |
| :--- | :--- | :--- |
| **🔍 智能全息识别** | 自动判别 URL 直链 / 影视剧名 / 电子小说 / P2P 协议 | 零学习成本，输入即解析 |
| **📖 原生小说阅读器** | 专研 `NovelReaderDialog` 架构，内嵌目次抽屉、字号调节、4大护眼主题与TXT全本导出 | 沉浸式小说阅读体验，媲美专业阅读应用 |
| **📚 绝版书籍全网穿透** | 在线小说目录抓取 + 夸克/百度网盘无删减精校 TXT/EPUB 挖掘 | 轻松搜得全网罕见、完本与冷门小说资源 |
| **🎬 影视流媒体秒播** | 接入 10 大开放核心节点，集成原生硬件加速硬解 | 在线秒开出画，免看广告与假下载 |
| **🌊 全网深潜挖掘模式** | 剧情线索/短视频文案逆向溯源 + 网盘暗搜 + 全球 DHT 磁力 | 解决“看片段找不到原片”与绝版资源搜寻难题 |
| **🌐 跨语言智能对齐** | 毫秒级多语言片名别名映射（如 Oppenheimer $\rightarrow$ 奥本海默） | 中英文双向互通秒出片源 |
| **📄 附件与软件纯净直通**| DOM 树二级穿透，校验 `Content-Disposition` 二进制流 | 过滤流氓捆绑下载器，直达真实原件 |
| **🌍 5国语言即时切换** | 简中 / 繁中 / English / 日本語 / 한국어 全局集中热切换 | 界面无死角同步，配置持久化 |

---

## 🏗 技术架构

```
┌──────────────────────────────────────────────────────────┐
│                   OmniFinder 核心调度引擎                 │
└──────────────┬────────────────────────────┬──────────────┘
               │                            │
       ┌───────┴────────┐          ┌────────┴────────┐
       ▼                ▼          ▼                 ▼
【网络嗅探层】    【全网聚合层】  【多媒体流解包】    【UI 渲染与播放】
• DOM 树穿透     • 10大影视云流  • M3U8 切片抓取   • PyQt5 桌面框架
• MIME 二进制识别 • 网盘暗河索引  • 原生多线程下载  • QWebEngine 沙箱
• CDP 协议层探针 • 全球 DHT 磁力 • FFmpeg 转码合并 • 硬件加速播放窗口
```

---

## 📁 目录结构说明

```plaintext
universal_scraper/
├── main_ui.py                 # 主窗口 UI、表格渲染、交互事件调度
├── resource_searcher.py       # 核心资源搜索引擎（深潜模式/逆向溯源/网盘暗搜/DHT磁力）
├── sniffer_engine.py          # 网络层与 DOM 深度嗅探探针
├── sniffer_magic.py           # 二进制文件指纹（Magic Number）识别库
├── downloader.py              # 流媒体多线程下载与 FFmpeg 合成引擎
├── player_server.py           # 本地流媒体代理服务（支持跨域与防盗链穿透）
├── i18n.py                    # 国际化管理总线（支持中/英/繁/日/韩）
├── build_exe.py               # Windows 本地 PyInstaller 单文件打包脚本
├── build_for_windows.bat      # Windows 一键全自动依赖安装与打包脚本
├── .github/workflows/
│   └── build.yml              # GitHub Actions 自动化云端交叉编译流水线
└── README.md                  # 项目中英文技术说明与合规文档
```

---

## 🚀 快速开始

### 方式一：下载绿色便携版（推荐）
无需配置 Python 环境，直接在 [GitHub Releases 页面](https://github.com/JackSunWuKong/Omnipotent/releases) 下载最新版的 **`OmniFinder.exe`**，双击即可直接运行。

### 方式二：从源码运行
```bash
# 1. 克隆代码仓库
git clone https://github.com/JackSunWuKong/Omnipotent.git
cd Omnipotent

# 2. 安装必要运行依赖
pip install PyQt5 PyQtWebEngine httpx beautifulsoup4 yt-dlp requests

# 3. 启动应用程序
python3 main_ui.py
```

---

## ⚖️ 免责声明 (Legal Disclaimer)

1. **学习与学术研究用途**：本软件仅供个人技术交流、网络协议工程探索及学术研究参考，不得用于任何商业盈利活动或侵权行为。
2. **数据来源说明**：本软件不存储、不制作、不修改任何第三方多媒体内容，所有检索与解析结果均来源于互联网开放公开协议及公开网络接口。
3. **法律遵从**：使用者须严格遵守所在国家与地区的版权法规与网络安全法律，任何因非合规使用而引发的纠纷均与本项目开发者无关。

---
---

# 🌐 English Documentation

## 📖 Overview
**OmniFinder** is an open-source desktop exploration tool designed for **computer network protocol analysis, media streaming & decoding, and multi-source information retrieval** research.

> [!NOTE]
> **Compliance Notice**: This project is strictly non-commercial and developed for personal educational research and technical experiments to analyze client-server interactions, stream segment reassembly, and cross-lingual semantic alignment.

---

## ✨ Key Features

- **🔍 Smart Auto-Routing**: Automatically identifies direct URLs, media titles, novels, or P2P/magnet protocols with zero learning curve.
- **📖 Native Novel & E-Book Reader**: Integrated `NovelReaderDialog` featuring TOC navigation, 4 eye-care themes, font scaling, and full-book TXT exporting.
- **📚 Deep Book Search Matrix**: Retrieves complete TOCs from open chapter aggregators + uncompressed TXT/EPUB collections from cloud drives.
- **🎬 Hardware Accelerated Streaming**: Connects to 10 verified high-speed nodes for instant playback via an embedded player.
- **🌊 Deep Dive Mode**: Includes plot/clue reverse search, cloud drive index traversal, and global decentralized DHT magnet discovery.
- **🌐 Cross-Lingual Title Mapping**: Real-time translation of foreign titles to canonical counterparts (e.g. *Oppenheimer* $\rightarrow$ *奥本海默*).
- **📄 Clean File Extraction**: Traverses DOM trees and verifies `Content-Disposition` headers to deliver clean binary downloads without bundled malware.
- **🌍 5 Global Languages**: Instant hot-switching between Simplified Chinese, Traditional Chinese, English, Japanese, and Korean.

---

## 🏗 Technical Architecture

```plaintext
                            ┌─────────────────────────────────┐
                            │    OmniFinder Core Dispatcher   │
                            └───────────────┬─────────────────┘
                                            │
         ┌──────────────────┬───────────────┴──────────────┬──────────────────┐
         ▼                  ▼                              ▼                  ▼
[Network Sniffer]  [Multi-Source Search]          [Media Stream Engine]  [UI & Player]
• DOM Penetration  • 10 High-Speed CMS Nodes      • M3U8 Segment Fetch   • PyQt5 Framework
• MIME Detection   • Cloud Drive Deep Index       • Multi-threaded DL    • QWebEngine Sandbox
• CDP Layer Probe  • Decentralized DHT Magnet     • FFmpeg Transcoding   • HW Accelerated Player
```

---

## 🚀 Quick Start

### Method 1: Portable Binary (Recommended)
Download the standalone **`OmniFinder.exe`** directly from [GitHub Releases](https://github.com/JackSunWuKong/Omnipotent/releases) without installing Python.

### Method 2: Run from Source
```bash
# Clone the repository
git clone https://github.com/JackSunWuKong/Omnipotent.git
cd Omnipotent

# Install dependencies
pip install PyQt5 PyQtWebEngine httpx beautifulsoup4 yt-dlp requests

# Launch the application
python3 main_ui.py
```

---

## ⚖️ Legal Disclaimer

1. **Non-Commercial Academic Use**: This application is strictly intended for educational study, network protocol exploration, and technical evaluation. Commercial use is strictly prohibited.
2. **Third-Party Content**: OmniFinder does not host, store, or alter any third-party multimedia content. All results are fetched dynamically from publicly accessible network endpoints and protocols.
3. **Compliance**: Users must adhere to their local laws and copyright regulations. The developers assume no liability for misuse.
