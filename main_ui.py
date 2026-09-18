"""
图形用户界面（基于 PyQt5 + PyQtWebEngine）
彻底解决 macOS / Windows 中文输入法（IME）上屏与焦点事件传递：
1. 重写 inputMethodEvent 与 inputMethodQuery，精准接收原生输入法的预编辑文本与最终上屏提交
2. 增加资源大小列与底部实时统计信息
3. 极速内置播放窗口
"""

import os
import sys
import subprocess
import threading
from urllib.parse import urlparse

# 确保在导入 QApplication 之前完全释放原生输入法通道
if "QT_IM_MODULE" in os.environ:
    del os.environ["QT_IM_MODULE"]

from PyQt5.QtCore import Qt, pyqtSignal, QObject, QUrl, QVariant, QByteArray, QTimer

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QTextEdit, QPlainTextEdit,
    QProgressBar, QSplitter, QGroupBox, QMessageBox, QDialog,
    QTabWidget, QSlider, QStyle, QScrollArea, QStackedWidget, QComboBox,
    QListWidget, QListWidgetItem, QTextBrowser
)

from PyQt5.QtWebEngineWidgets import QWebEngineView

from PyQt5.QtGui import QInputMethodEvent, QPixmap, QIcon, QFont, QDesktopServices

from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget

from sniffer_engine import SnifferEngine
from downloader import Downloader
from resource_searcher import ResourceSearcher
from player_server import get_proxy_stream_url
from i18n import tr, get_i18n


def format_size_str(size_bytes: int, is_stream=False):
    """格式化资源大小展示"""
    if size_bytes and size_bytes > 0:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    elif is_stream:
        return tr("size_hd_stream")
    return tr("size_unknown")


def open_media_with_system(media_source: str):
    """跨平台调用系统播放器打开本地已下载好的视频"""
    try:
        if sys.platform == "win32":
            os.startfile(media_source)
        elif sys.platform == "darwin":
            subprocess.run(["open", media_source])
        else:
            subprocess.run(["xdg-open", media_source])
        return True
    except Exception:
        return False


class ChineseFriendlyLineEdit(QPlainTextEdit):
    """
    原生中文输入法深度适配输入框：
    利用 QPlainTextEdit 挂载的原生 Cocoa 文本总线（NSTextView），
    彻底解决 macOS / Windows Qt5 中 QLineEdit 无法调出中文输入法、
    无法显示拼音候选词框或输入法被强制锁定为英文的系统级缺陷。
    """
    returnPressed = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFixedHeight(34)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setAttribute(Qt.WA_InputMethodEnabled, True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #ffffff;
                color: #24292e;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
            }
            QPlainTextEdit:focus {
                border: 1.5px solid #2196F3;
            }
        """)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.returnPressed.emit()
            e.accept()
            return
        elif e.key() == Qt.Key_Tab:
            self.focusNextChild()
            e.accept()
            return
        super().keyPressEvent(e)

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        self.setFocus(Qt.MouseFocusReason)

    def insertFromMimeData(self, source):
        # 过滤粘贴文本中的换行，保持单行
        raw = source.text().replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
        self.insertPlainText(raw)

    def text(self) -> str:
        return self.toPlainText().replace("\r\n", "").replace("\n", "").replace("\r", "").strip()

    def setText(self, text: str):
        self.setPlainText(str(text) if text else "")


class EmbeddedPlayerDialog(QDialog):
    """
    原生硬件加速视频播放弹窗（真正集成在软件内部的极速秒播窗口）
    底层由 macOS AVFoundation / Windows Media Foundation 原生硬件硬解引擎驱动，
    彻底淘汰 QWebEngineView (避开其无法硬解 H.264/AAC 专利视频的致命缺陷)，
    实现任何在线 m3u8 / mp4 的毫秒级极速起播！
    """
    def __init__(self, video_url: str, title: str = "正在播放", referer: str = "", parent=None):
        super().__init__(parent)
        self.video_url = video_url
        self.referer = referer
        self.title_text = title
        self.setWindowTitle(tr("player_title", title=title))
        self.resize(1020, 640)
        self.setStyleSheet("background-color: #0d1117; color: #ffffff;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. 顶部状态与工具栏
        top_bar = QWidget()
        top_bar.setStyleSheet("background-color: #161b22; border-bottom: 1px solid #30363d;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(14, 8, 14, 8)

        title_lbl = QLabel(f"🎬 {title}")
        title_lbl.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 14px;")
        top_layout.addWidget(title_lbl)

        self.status_lbl = QLabel(tr("player_status_loading"))
        self.status_lbl.setStyleSheet("color: #00C853; font-size: 12px; margin-left: 12px;")
        top_layout.addWidget(self.status_lbl)

        top_layout.addStretch()

        self.btn_sys = QPushButton(tr("player_btn_sys"))
        self.btn_sys.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                font-weight: bold;
                padding: 5px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #2ea043; }
        """)
        self.btn_sys.clicked.connect(self.play_with_system_direct)
        top_layout.addWidget(self.btn_sys)

        self.btn_copy = QPushButton(tr("player_btn_copy"))
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                padding: 5px 10px;
                border: 1px solid #30363d;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #30363d; }
        """)
        self.btn_copy.clicked.connect(self.copy_url)
        top_layout.addWidget(self.btn_copy)

        layout.addWidget(top_bar)

        # 2. 原生硬件视频播放视口
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: #000000;")
        layout.addWidget(self.video_widget, 1)

        # 3. 底部播放控制面板
        control_bar = QWidget()
        control_bar.setStyleSheet("background-color: #161b22; border-top: 1px solid #30363d;")
        ctrl_layout = QHBoxLayout(control_bar)
        ctrl_layout.setContentsMargins(14, 8, 14, 8)
        ctrl_layout.setSpacing(10)

        # 播放/暂停按钮
        self.btn_play = QPushButton("⏸")
        self.btn_play.setFixedSize(36, 30)
        self.btn_play.setStyleSheet("font-size: 15px; font-weight: bold; background-color: #00C853; color: white; border-radius: 4px;")
        self.btn_play.clicked.connect(self.toggle_play)
        ctrl_layout.addWidget(self.btn_play)

        # 进度时间标签
        self.time_lbl = QLabel("00:00 / 00:00")
        self.time_lbl.setStyleSheet("color: #8b949e; font-size: 12px; min-width: 95px;")
        ctrl_layout.addWidget(self.time_lbl)

        # 进度滑动条
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 6px; background: #30363d; border-radius: 3px; }
            QSlider::sub-page:horizontal { background: #00C853; border-radius: 3px; }
            QSlider::handle:horizontal { background: #ffffff; width: 14px; margin-top: -4px; margin-bottom: -4px; border-radius: 7px; }
        """)
        self.slider.sliderMoved.connect(self.set_position)
        ctrl_layout.addWidget(self.slider, 1)

        # 音量控制
        vol_icon = QLabel("🔊")
        vol_icon.setStyleSheet("font-size: 14px;")
        ctrl_layout.addWidget(vol_icon)

        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(80)
        self.vol_slider.setFixedWidth(80)
        self.vol_slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 4px; background: #30363d; border-radius: 2px; }
            QSlider::sub-page:horizontal { background: #58a6ff; border-radius: 2px; }
            QSlider::handle:horizontal { background: #ffffff; width: 10px; margin-top: -3px; margin-bottom: -3px; border-radius: 5px; }
        """)
        self.vol_slider.valueChanged.connect(self.set_volume)
        ctrl_layout.addWidget(self.vol_slider)

        # 全屏切换按钮
        self.btn_fullscreen = QPushButton(tr("player_fullscreen"))
        self.btn_fullscreen.setStyleSheet("background-color: #21262d; color: #c9d1d9; padding: 4px 8px; border: 1px solid #30363d; border-radius: 4px;")
        self.btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        ctrl_layout.addWidget(self.btn_fullscreen)

        layout.addWidget(control_bar)

        # 4. 初始化底层 QMediaPlayer
        self.player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.player.setVideoOutput(self.video_widget)
        self.player.setVolume(80)

        self.player.stateChanged.connect(self.on_state_changed)
        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.player.error.connect(self.on_media_error)

        # 启动播放（通过本地回环代理自动注入防盗链 Referer 并重写 TS 切片，0 错误秒播）
        if os.path.exists(video_url):
            self.play_url = video_url
            media_content = QMediaContent(QUrl.fromLocalFile(video_url))
        else:
            self.play_url = get_proxy_stream_url(video_url, referer=referer)
            media_content = QMediaContent(QUrl(self.play_url))
        self.player.setMedia(media_content)
        self.player.play()

    def play_with_system_direct(self):
        open_media_with_system(self.play_url)

    def toggle_play(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def on_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.btn_play.setText("⏸")
        else:
            self.btn_play.setText("▶")

    def on_position_changed(self, position):
        if not self.slider.isSliderDown():
            self.slider.setValue(position)
        self.update_time_label(position, self.player.duration())

    def on_duration_changed(self, duration):
        self.slider.setRange(0, duration)
        self.update_time_label(self.player.position(), duration)

    def set_position(self, position):
        self.player.setPosition(position)

    def set_volume(self, value):
        self.player.setVolume(value)

    def update_time_label(self, pos_ms, dur_ms):
        pos_sec = max(0, pos_ms // 1000)
        dur_sec = max(0, dur_ms // 1000)
        pos_str = f"{pos_sec // 60:02d}:{pos_sec % 60:02d}"
        dur_str = f"{dur_sec // 60:02d}:{dur_sec % 60:02d}"
        if dur_sec >= 3600:
            pos_str = f"{pos_sec // 3600:02d}:{(pos_sec % 3600) // 60:02d}:{pos_sec % 60:02d}"
            dur_str = f"{dur_sec // 3600:02d}:{(dur_sec % 3600) // 60:02d}:{dur_sec % 60:02d}"
        self.time_lbl.setText(f"{pos_str} / {dur_str}")

    def on_media_status_changed(self, status):
        if status in [QMediaPlayer.BufferedMedia, QMediaPlayer.BufferingMedia]:
            self.status_lbl.setText(tr("player_status_playing"))
            self.status_lbl.setStyleSheet("color: #00C853; font-size: 12px; margin-left: 12px;")
        elif status == QMediaPlayer.LoadingMedia:
            self.status_lbl.setText(tr("player_status_loading"))
            self.status_lbl.setStyleSheet("color: #58a6ff; font-size: 12px; margin-left: 12px;")
        elif status == QMediaPlayer.EndOfMedia:
            self.btn_play.setText("▶")

    def on_media_error(self, error):
        err_msg = self.player.errorString()
        self.status_lbl.setText(tr("player_status_error", err=err_msg))
        self.status_lbl.setStyleSheet("color: #f85149; font-size: 12px; margin-left: 12px;")

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.btn_fullscreen.setText(tr("player_fullscreen"))
        else:
            self.showFullScreen()
            self.btn_fullscreen.setText(tr("player_exit_fullscreen"))

    def copy_url(self):
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.video_url)
            QMessageBox.information(self, tr("msg_tip"), tr("stream_link_copied"))

    def closeEvent(self, event):
        self.player.stop()
        event.accept()


class ResourcePreviewDialog(QDialog):
    """
    终极万能沉浸式资源预览窗口：
    不管是样张大图、多层跳转的复杂网页/门户平台、软件安装镜像，全部支持即时预览与深度穿透！
    1. 拥有样张图片：毫秒级渲染样张大图
    2. 网页/平台/复杂跳转：多层跳转自动追踪 + 深度嗅探直连资源 + 内嵌微内核极速全景网页交互预览
    """
    download_requested = pyqtSignal(dict)
    image_loaded_signal = pyqtSignal(bytes)
    image_failed_signal = pyqtSignal()
    deep_sniff_finished_signal = pyqtSignal(list, str)  # 穿透捕获到的资源列表, 终点页面标题

    def __init__(self, resource_item: dict, parent=None):
        super().__init__(parent)
        self.item = resource_item
        title = self.item.get("label", tr("category_unknown"))
        self.setWindowTitle(tr("preview_title", title=title))
        self.resize(920, 680)
        self.setStyleSheet("""
            QDialog { background-color: #f6f8fa; color: #24292e; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # 1. 顶部标题栏与穿透状态
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: #ffffff; border: 1px solid #e1e4e8; border-radius: 6px; padding: 8px;")
        h_layout = QVBoxLayout(header_widget)
        h_layout.setContentsMargins(12, 8, 12, 8)

        self.lbl_title = QLabel(f"<b>{title}</b>")
        self.lbl_title.setStyleSheet("font-size: 15px; color: #0366d6;")
        self.lbl_title.setWordWrap(True)
        h_layout.addWidget(self.lbl_title)

        raw_cat = self.item.get('category', 'other')
        cat_name = tr(f"cat_{raw_cat}") if f"cat_{raw_cat}" in get_i18n().get_all_keys() else tr("category_unknown")
        meta_info = tr("preview_type", cat=cat_name, ext=self.item.get('ext', ''), source=self.item.get('source_engine', tr('source_default')))
        self.lbl_meta = QLabel(meta_info)
        self.lbl_meta.setStyleSheet("color: #586069; font-size: 12px; margin-top: 3px;")
        h_layout.addWidget(self.lbl_meta)
        layout.addWidget(header_widget)

        # 2. 中间多模式沉浸式预览视口 (QStackedWidget)
        # Page 0: 图片/大样张预览模式 (QScrollArea)
        # Page 1: 复杂页面/平台实时微内核内嵌全景渲染 (QWebEngineView)
        self.stack = QStackedWidget()

        # --- 模式 1: 图像/文档样张 ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background-color: #ffffff; border: 1px solid #d1d5db; border-radius: 6px;")

        self.preview_content = QWidget()
        self.pc_layout = QVBoxLayout(self.preview_content)
        self.pc_layout.setAlignment(Qt.AlignCenter)
        self.pc_layout.setContentsMargins(16, 16, 16, 16)

        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setStyleSheet("color: #888; font-size: 13px;")
        self.pc_layout.addWidget(self.img_label)
        self.scroll.setWidget(self.preview_content)
        self.stack.addWidget(self.scroll)

        # --- 模式 2: 网页/平台微内核即时渲染视口 ---
        self.web_container = QWidget()
        self.web_layout = QVBoxLayout(self.web_container)
        self.web_layout.setContentsMargins(0, 0, 0, 0)
        self.web_layout.setSpacing(6)

        self.web_status_lbl = QLabel(tr("preview_web_loading"))
        self.web_status_lbl.setStyleSheet("color: #0366d6; font-size: 12px; padding: 4px 8px; background-color: #f1f8ff; border: 1px solid #c8e1ff; border-radius: 4px;")
        self.web_layout.addWidget(self.web_status_lbl)

        self.web_view = QWebEngineView()
        self.web_view.setStyleSheet("border: 1px solid #d1d5db; border-radius: 6px; background-color: #ffffff;")
        self.web_view.loadFinished.connect(self._inject_adblock_script)
        self.web_layout.addWidget(self.web_view, 1)
        self.stack.addWidget(self.web_container)

        layout.addWidget(self.stack, 1)

        # --- 穿透发现内嵌直出资源条 (若追踪多层后发现真实附件/下载包，显示此醒目横条) ---
        self.found_box = QWidget()
        self.found_box.setVisible(False)
        self.found_box.setStyleSheet("background-color: #e6ffed; border: 1px solid #acf2bd; border-radius: 6px; padding: 8px;")
        fb_layout = QHBoxLayout(self.found_box)
        fb_layout.setContentsMargins(10, 6, 10, 6)

        self.found_lbl = QLabel(tr("preview_found_link", title=title, ext=self.item.get('ext', '')))
        self.found_lbl.setStyleSheet("color: #22863a; font-weight: bold; font-size: 13px;")
        fb_layout.addWidget(self.found_lbl, 1)

        self.btn_found_down = QPushButton(tr("preview_btn_found_down"))
        self.btn_found_down.setStyleSheet("background-color: #2ea44f; color: white; font-weight: bold; padding: 5px 14px; border-radius: 4px;")
        self.btn_found_down.clicked.connect(self._on_found_download)
        fb_layout.addWidget(self.btn_found_down)
        layout.addWidget(self.found_box)

        # 3. 底部操作按键栏
        btn_bar = QHBoxLayout()
        btn_bar.setContentsMargins(0, 4, 0, 0)

        self.btn_browser = QPushButton(tr("preview_btn_browser"))
        self.btn_browser.setStyleSheet("background-color: #ffffff; border: 1px solid #d1d5db; padding: 7px 14px; border-radius: 4px; font-size: 13px;")
        self.btn_browser.clicked.connect(lambda: open_media_with_system(self.item.get("url", "")))
        btn_bar.addWidget(self.btn_browser)

        self.btn_copy = QPushButton(tr("preview_btn_copy"))
        self.btn_copy.setStyleSheet("background-color: #ffffff; border: 1px solid #d1d5db; padding: 7px 14px; border-radius: 4px; font-size: 13px;")
        self.btn_copy.clicked.connect(self.copy_link)
        btn_bar.addWidget(self.btn_copy)

        self.btn_toggle_view = QPushButton(tr("preview_btn_toggle"))
        self.btn_toggle_view.setStyleSheet("background-color: #f1f8ff; border: 1px solid #c8e1ff; color: #0366d6; padding: 7px 14px; border-radius: 4px; font-size: 13px;")
        self.btn_toggle_view.clicked.connect(self._toggle_view_mode)
        btn_bar.addWidget(self.btn_toggle_view)

        btn_bar.addStretch()

        self.btn_down = QPushButton(tr("preview_btn_down"))
        self.btn_down.setStyleSheet("""
            QPushButton {
                background-color: #2ea44f;
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
                padding: 7px 18px;
                border-radius: 4px;
                border: 1px solid rgba(27,31,35,.15);
            }
            QPushButton:hover { background-color: #2c974b; }
        """)
        self.btn_down.clicked.connect(self.confirm_download)
        btn_bar.addWidget(self.btn_down)

        self.btn_close = QPushButton(tr("preview_btn_close"))
        self.btn_close.setStyleSheet("background-color: #f3f4f6; border: 1px solid #d1d5db; padding: 7px 14px; border-radius: 4px; font-size: 13px;")
        self.btn_close.clicked.connect(self.close)
        btn_bar.addWidget(self.btn_close)

        layout.addLayout(btn_bar)

        self.image_loaded_signal.connect(self._on_image_loaded)
        self.image_failed_signal.connect(self._on_image_failed)
        self.deep_sniff_finished_signal.connect(self._on_deep_sniff_finished)

        self._best_download_item = self.item
        self._init_preview_pipeline()

    def _init_preview_pipeline(self):
        cat = self.item.get("category", "")
        p_img = self.item.get("preview_img", "")
        res_url = self.item.get("url", "")

        # 1. 如果有明确样张大图，优先展示大图
        if p_img or cat == "image":
            self.stack.setCurrentIndex(0)
            self.img_label.setText(tr("preview_img_loading"))
            target_img_url = p_img if p_img else res_url
            self._fetch_image_async(target_img_url)

        # 2. 如果是网页、门户或者跳转链接，启动微内核内嵌全景渲染 + 异步多层深度穿透
        elif res_url.startswith("http://") or res_url.startswith("https://"):
            # 切换到全景浏览器渲染视口
            self.stack.setCurrentIndex(1)
            self.web_status_lbl.setText(tr("preview_rendering_target", url=res_url))
            self.web_view.setUrl(QUrl(res_url))

            # 同时启动后台多层穿透跟踪（追踪多层重定向与真实隐藏下载附件）
            threading.Thread(target=self._deep_sniff_worker, args=(res_url,), daemon=True).start()

        else:
            self.stack.setCurrentIndex(0)
            self.img_label.setText(tr("preview_direct_url_tip", url=res_url))

    def _fetch_image_async(self, img_url: str):
        def worker():
            try:
                import httpx
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Referer": self.item.get("referer", "https://sc.chinaz.com/")
                }
                r = httpx.get(img_url, timeout=7.0, headers=headers, verify=False)
                if r.status_code == 200 and len(r.content) > 0:
                    self.image_loaded_signal.emit(r.content)
                    return
            except Exception:
                pass
            self.image_failed_signal.emit()

        threading.Thread(target=worker, daemon=True).start()

    def _deep_sniff_worker(self, initial_url: str):
        """后台多层穿透嗅探：即使跳转多层也能挖掘出最终直下文件与高清样张"""
        try:
            import httpx
            from bs4 import BeautifulSoup
            from urllib.parse import urljoin
            with httpx.Client(timeout=6.0, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True, verify=False) as c:
                r = c.get(initial_url)
                final_url = str(r.url)
                soup = BeautifulSoup(r.text, "html.parser")
                page_title = soup.title.string.strip() if soup.title and soup.title.string else ""

                found_downloads = []
                # 扫描所有下载直链
                for a in soup.find_all("a", href=True):
                    h = a["href"].strip()
                    full_link = urljoin(final_url, h)
                    low = full_link.lower().split("?")[0]
                    if any(low.endswith(ext) for ext in [".rar", ".zip", ".doc", ".docx", ".pdf", ".7z", ".exe", ".dmg", ".pkg"]):
                        t = a.get_text(strip=True) or os.path.basename(low)
                        ext = low.split(".")[-1]
                        found_downloads.append({
                            "url": full_link,
                            "label": t,
                            "ext": ext,
                            "category": "document" if ext in ["doc", "docx", "pdf"] else "archive",
                            "referer": final_url
                        })

                # 扫描正文大图（如果页面有预览样张）
                imgs = [urljoin(final_url, img.get("src") or "") for img in soup.find_all("img") if img.get("src")]
                valid_imgs = [i for i in imgs if any(ext in i.lower() for ext in [".jpg", ".png", ".jpeg"]) and not any(k in i.lower() for k in ["logo", "icon", "avatar"])]
                if valid_imgs and not self.item.get("preview_img"):
                    self._fetch_image_async(valid_imgs[0])

                self.deep_sniff_finished_signal.emit(found_downloads[:5], page_title)
        except Exception:
            pass

    def _on_deep_sniff_finished(self, found_list: list, page_title: str):
        if page_title:
            self.lbl_title.setText(f"<b>{page_title}</b>")
        if found_list:
            top_file = found_list[0]
            self._best_download_item = top_file
            self.found_lbl.setText(tr("preview_found_link", title=top_file.get("label", tr("attachment_pkg")), ext=top_file.get("ext", "")))
            self.web_status_lbl.setText(tr("preview_found_status", count=len(found_list)))
            self.found_box.setVisible(True)
            self.web_status_lbl.setText(f"✨ 穿透引擎已为您在目标页面中锁定 {len(found_list)} 个直出文件，可直接点击下方绿钮高速下载！")

    def _on_found_download(self):
        self.download_requested.emit(self._best_download_item)
        self.close()

    def _inject_adblock_script(self, ok):
        """实时注入全局 CSS 屏蔽样式与广告拦截 JS，彻底拔除网页浮动广告与弹窗"""
        if not ok:
            return
        adblock_js = """
        (function() {
            // 1. 注入强力广告拦截 CSS
            const style = document.createElement('style');
            style.type = 'text/css';
            style.innerHTML = `
                [class*="ad-"], [id*="advert"], [class*="advert"], [class*="banner"],
                [id*="banner"], [class*="popup"], [id*="popup"], [class*="fixed-ad"],
                iframe[src*="union"], iframe[src*="ad"], iframe[src*="pos"],
                .adsbygoogle, .gg-box, .side-ad, .bottom-bar, .float-bar,
                #BAIDU_SSP__wrapper, [id*="cproIframe"], .header-ad, .footer-ad {
                    display: none !important;
                    visibility: hidden !important;
                    opacity: 0 !important;
                    pointer-events: none !important;
                    height: 0 !important;
                }
            `;
            document.head.appendChild(style);

            // 2. 遍历并移除已知广告悬浮节点
            const adSelectors = [
                'iframe[src*="pos"]', 'iframe[src*="ad"]', 'iframe[src*="union"]',
                '.ad-box', '.gg-box', '#couplet', '.popup-ad'
            ];
            adSelectors.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => el.remove());
            });
        })();
        """
        self.web_view.page().runJavaScript(adblock_js)

    def _toggle_view_mode(self):
        curr = self.stack.currentIndex()
        next_idx = 1 if curr == 0 else 0
        self.stack.setCurrentIndex(next_idx)
        if next_idx == 1 and not self.web_view.url().isValid():
            self.web_view.setUrl(QUrl(self.item.get("url", "")))

    def _on_image_loaded(self, data: bytes):
        try:
            pix = QPixmap()
            pix.loadFromData(QByteArray(data))
            if not pix.isNull():
                scaled = pix.scaled(720, 540, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.img_label.setPixmap(scaled)
                return
        except Exception:
            pass
        self._on_image_failed()

    def _on_image_failed(self):
        # 若图片失败且为有效网页，自动切换至微内核内嵌视口
        res_url = self.item.get("url", "")
        if res_url.startswith("http://") or res_url.startswith("https://"):
            self.stack.setCurrentIndex(1)
        else:
            self.img_label.setText(tr("preview_img_tip"))

    def copy_link(self):
        QApplication.clipboard().setText(self._best_download_item.get("url", ""))
        QMessageBox.information(self, tr("msg_tip"), tr("preview_link_copied"))

    def confirm_download(self):
        self.download_requested.emit(self._best_download_item)
        self.close()


class NovelReaderDialog(QDialog):
    """
    专用小说原生极速阅读视口（集章节目录、排版字体调节、护眼主题、全本导出于一体）
    具备现代电子书软件的标准体验：
    1. 章节目录侧边抽屉，实时快速检索与无缝跳转
    2. 四大经典阅读主题（护眼绿、典雅羊皮纸、夜间暗黑、简约纯白）
    3. 自由字号缩放 (A- / A+) 与排版优化
    4. 上一章 / 下一章平滑切章与进度百分比
    5. 一键导出整本小说至本地纯文本 (.txt)
    """
    chapter_loaded_signal = pyqtSignal(str, str) # title, content
    chapters_ready_signal = pyqtSignal(list)      # chapter list

    THEMES = {
        "green": {
            "name_key": "reader_theme_green",
            "bg": "#CCE8CF",
            "text": "#1B3B22",
            "sidebar_bg": "#BBDDBE",
            "sidebar_text": "#1B3B22",
            "border": "#A4CBA8"
        },
        "parchment": {
            "name_key": "reader_theme_parchment",
            "bg": "#F5EEDC",
            "text": "#3D2B1F",
            "sidebar_bg": "#ECE2CD",
            "sidebar_text": "#3D2B1F",
            "border": "#D8CAB0"
        },
        "dark": {
            "name_key": "reader_theme_dark",
            "bg": "#1E1E1E",
            "text": "#D4D4D4",
            "sidebar_bg": "#252526",
            "sidebar_text": "#CCCCCC",
            "border": "#3E3E42"
        },
        "white": {
            "name_key": "reader_theme_white",
            "bg": "#FFFFFF",
            "text": "#24292E",
            "sidebar_bg": "#F6F8FA",
            "sidebar_text": "#24292E",
            "border": "#E1E4E8"
        }
    }

    def __init__(self, book_info: dict, parent=None):
        super().__init__(parent)
        self.book_info = book_info
        self.book_url = book_info.get("url", "")
        self.book_title = book_info.get("label", "小说阅读").split("]")[0].replace("📖 《", "").replace("》", "").strip()
        if "《" in self.book_title and "》" in self.book_title:
            self.book_title = self.book_title[self.book_title.find("《")+1:self.book_title.find("》")]

        self.setWindowTitle(tr("reader_title", title=self.book_title))
        self.resize(1080, 720)
        self.current_theme = "green"
        self.font_size = 18
        self.all_chapters = []
        self.current_chapter_idx = 0

        self.chapter_loaded_signal.connect(self._on_chapter_loaded)
        self.chapters_ready_signal.connect(self._on_chapters_ready)

        self._init_ui()
        self._apply_theme()
        self._fetch_toc_async()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. 顶部控制工具栏
        self.top_bar = QWidget()
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(16, 10, 16, 10)
        top_layout.setSpacing(12)

        self.title_lbl = QLabel(f"📖 <b>《{self.book_title}》</b>")
        self.title_lbl.setStyleSheet("font-size: 15px; font-weight: bold;")
        top_layout.addWidget(self.title_lbl)

        top_layout.addStretch()

        # 字号缩放
        btn_smaller = QPushButton(tr("reader_font_smaller"))
        btn_smaller.setCursor(Qt.PointingHandCursor)
        btn_smaller.clicked.connect(self._decrease_font)
        top_layout.addWidget(btn_smaller)

        btn_larger = QPushButton(tr("reader_font_larger"))
        btn_larger.setCursor(Qt.PointingHandCursor)
        btn_larger.clicked.connect(self._increase_font)
        top_layout.addWidget(btn_larger)

        # 主题切换按钮组
        for theme_key in ["green", "parchment", "dark", "white"]:
            btn_t = QPushButton(tr(self.THEMES[theme_key]["name_key"]))
            btn_t.setCursor(Qt.PointingHandCursor)
            btn_t.clicked.connect(lambda chk, tk=theme_key: self._set_theme(tk))
            top_layout.addWidget(btn_t)

        # 导出全本 TXT
        self.btn_export = QPushButton(tr("reader_export_txt"))
        self.btn_export.setStyleSheet("background-color: #00897B; color: white; font-weight: bold; border-radius: 4px; padding: 5px 12px;")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.clicked.connect(self._export_full_txt)
        top_layout.addWidget(self.btn_export)

        main_layout.addWidget(self.top_bar)

        # 2. 中间主体（左目录 + 右阅读正文）
        self.splitter = QSplitter(Qt.Horizontal)

        # 左侧目录抽屉
        self.toc_container = QWidget()
        toc_layout = QVBoxLayout(self.toc_container)
        toc_layout.setContentsMargins(10, 10, 10, 10)
        toc_layout.setSpacing(8)

        self.toc_header = QLabel(tr("reader_toc"))
        self.toc_header.setStyleSheet("font-weight: bold; font-size: 14px;")
        toc_layout.addWidget(self.toc_header)

        self.toc_filter = QLineEdit()
        self.toc_filter.setPlaceholderText(tr("reader_toc_search"))
        self.toc_filter.textChanged.connect(self._filter_toc)
        toc_layout.addWidget(self.toc_filter)

        self.toc_list = QListWidget()
        self.toc_list.itemClicked.connect(self._on_toc_clicked)
        toc_layout.addWidget(self.toc_list, 1)

        self.splitter.addWidget(self.toc_container)

        # 右侧阅读正文面板
        self.reading_container = QWidget()
        reading_layout = QVBoxLayout(self.reading_container)
        reading_layout.setContentsMargins(24, 16, 24, 16)
        reading_layout.setSpacing(10)

        self.chapter_title_lbl = QLabel("")
        self.chapter_title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; padding-bottom: 8px;")
        self.chapter_title_lbl.setAlignment(Qt.AlignCenter)
        reading_layout.addWidget(self.chapter_title_lbl)

        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(False)
        self.text_browser.setStyleSheet("border: none; padding: 10px;")
        reading_layout.addWidget(self.text_browser, 1)

        self.splitter.addWidget(self.reading_container)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 4)
        main_layout.addWidget(self.splitter, 1)

        # 3. 底部导航栏（上一章 / 进度 / 下一章）
        self.bottom_bar = QWidget()
        btm_layout = QHBoxLayout(self.bottom_bar)
        btm_layout.setContentsMargins(20, 10, 20, 10)

        self.btn_prev = QPushButton(tr("reader_prev_ch"))
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        self.btn_prev.clicked.connect(self._prev_chapter)
        btm_layout.addWidget(self.btn_prev)

        btm_layout.addStretch()

        self.progress_lbl = QLabel("0 / 0 (0%)")
        self.progress_lbl.setStyleSheet("font-size: 13px; font-weight: bold;")
        btm_layout.addWidget(self.progress_lbl)

        btm_layout.addStretch()

        self.btn_next = QPushButton(tr("reader_next_ch"))
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.clicked.connect(self._next_chapter)
        btm_layout.addWidget(self.btn_next)

        main_layout.addWidget(self.bottom_bar)

    def _apply_theme(self):
        th = self.THEMES[self.current_theme]
        bg = th["bg"]
        txt = th["text"]
        s_bg = th["sidebar_bg"]
        s_txt = th["sidebar_text"]
        bd = th["border"]

        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; color: {txt}; }}
            QWidget#top_bar {{ background-color: {s_bg}; border-bottom: 1px solid {bd}; }}
            QWidget#bottom_bar {{ background-color: {s_bg}; border-top: 1px solid {bd}; }}
            QPushButton {{
                background-color: {s_bg};
                color: {s_txt};
                border: 1px solid {bd};
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {bd}; }}
            QLineEdit {{
                background-color: {bg};
                color: {txt};
                border: 1px solid {bd};
                border-radius: 4px;
                padding: 4px 8px;
            }}
        """)

        self.top_bar.setObjectName("top_bar")
        self.bottom_bar.setObjectName("bottom_bar")
        self.toc_container.setStyleSheet(f"background-color: {s_bg}; border-right: 1px solid {bd};")
        self.toc_header.setStyleSheet(f"color: {s_txt}; font-size: 14px; font-weight: bold;")
        self.toc_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {s_bg};
                color: {s_txt};
                border: none;
                outline: none;
                font-size: 13px;
            }}
            QListWidget::item {{
                padding: 6px 8px;
                border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {bd};
                color: {txt};
                font-weight: bold;
            }}
        """)

        self.reading_container.setStyleSheet(f"background-color: {bg};")
        self.chapter_title_lbl.setStyleSheet(f"color: {txt}; font-size: 21px; font-weight: bold;")
        self.text_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {bg};
                color: {txt};
                border: none;
                font-family: 'PingFang SC', 'Microsoft YaHei', 'SimSun', serif;
                font-size: {self.font_size}px;
                line-height: 1.8;
                padding: 10px 24px;
            }}
        """)
        self.progress_lbl.setStyleSheet(f"color: {txt}; font-size: 13px;")

    def _set_theme(self, theme_name: str):
        self.current_theme = theme_name
        self._apply_theme()

    def _decrease_font(self):
        if self.font_size > 12:
            self.font_size -= 2
            self._apply_theme()

    def _increase_font(self):
        if self.font_size < 36:
            self.font_size += 2
            self._apply_theme()

    def _fetch_toc_async(self):
        self.text_browser.setPlainText(tr("reader_loading_ch"))
        def worker():
            chs = ResourceSearcher.fetch_novel_chapters(self.book_url)
            self.chapters_ready_signal.emit(chs)
        threading.Thread(target=worker, daemon=True).start()

    def _on_chapters_ready(self, chapters: list):
        self.all_chapters = chapters
        self.toc_list.clear()
        for idx, ch in enumerate(chapters):
            item = QListWidgetItem(ch["title"])
            item.setData(Qt.UserRole, idx)
            self.toc_list.addItem(item)

        if chapters:
            self._load_chapter(0)
        else:
            self.text_browser.setPlainText("未成功提取到在线目录，该书可能为纯网盘转存资源。您可点击下载全本保存至本地阅读。")

    def _filter_toc(self, text: str):
        keyword = text.strip().lower()
        for i in range(self.toc_list.count()):
            it = self.toc_list.item(i)
            it.setHidden(keyword not in it.text().lower())

    def _load_chapter(self, index: int):
        if not (0 <= index < len(self.all_chapters)):
            return
        self.current_chapter_idx = index
        self.toc_list.setCurrentRow(index)
        ch = self.all_chapters[index]
        self.chapter_title_lbl.setText(ch["title"])
        self.text_browser.setPlainText(tr("reader_loading_ch"))

        total = len(self.all_chapters)
        pct = int(((index + 1) / total) * 100) if total > 0 else 0
        self.progress_lbl.setText(f"{index + 1} / {total} ({pct}%)")

        self.btn_prev.setEnabled(index > 0)
        self.btn_next.setEnabled(index < total - 1)

        def worker():
            t, content = ResourceSearcher.fetch_chapter_content(ch["url"])
            self.chapter_loaded_signal.emit(t or ch["title"], content)

        threading.Thread(target=worker, daemon=True).start()

    def _on_chapter_loaded(self, title: str, content: str):
        self.chapter_title_lbl.setText(title)
        self.text_browser.setPlainText(content)
        self.text_browser.verticalScrollBar().setValue(0)

    def _on_toc_clicked(self, item: QListWidgetItem):
        idx = item.data(Qt.UserRole)
        self._load_chapter(idx)

    def _prev_chapter(self):
        if self.current_chapter_idx > 0:
            self._load_chapter(self.current_chapter_idx - 1)

    def _next_chapter(self):
        if self.current_chapter_idx < len(self.all_chapters) - 1:
            self._load_chapter(self.current_chapter_idx + 1)

    def _export_full_txt(self):
        if not self.all_chapters:
            QMessageBox.warning(self, tr("msg_tip"), "暂无可导出的章节内容。")
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "导出全本 TXT", f"{self.book_title}.txt", "Text Files (*.txt)")
        if not save_path:
            return

        # 异步后台批量爬取章节合成 TXT
        self.btn_export.setEnabled(False)
        self.btn_export.setText("正在导出...")

        def export_worker():
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(f"《{self.book_title}》\n\n")
                    for i, ch in enumerate(self.all_chapters):
                        t, content = ResourceSearcher.fetch_chapter_content(ch["url"])
                        f.write(f"{t or ch['title']}\n\n")
                        f.write(content + "\n\n" + "="*40 + "\n\n")
                QTimer.singleShot(0, lambda: QMessageBox.information(self, tr("msg_tip"), tr("reader_export_done", path=save_path)))
            except Exception as e:
                QTimer.singleShot(0, lambda: QMessageBox.warning(self, tr("msg_tip"), f"导出失败: {e}"))
            finally:
                QTimer.singleShot(0, lambda: (self.btn_export.setEnabled(True), self.btn_export.setText(tr("reader_export_txt"))))

        threading.Thread(target=export_worker, daemon=True).start()


class WorkerSignals(QObject):

    log_signal = pyqtSignal(str)
    scan_finished = pyqtSignal(list)
    progress_signal = pyqtSignal(int)
    download_finished = pyqtSignal(list)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("万象探索 (OmniFinder) - 个人网络多媒体与资源探索助手 (学习研究版)")
        self.resize(1150, 820)

        self.signals = WorkerSignals()
        self.signals.log_signal.connect(self.append_log)
        self.signals.scan_finished.connect(self.on_scan_finished)
        self.signals.progress_signal.connect(self.update_progress)
        self.signals.download_finished.connect(self.on_download_finished)

        self.all_resources = []
        self.downloaded_video_files = []
        self.save_dir = os.path.join(os.path.expanduser("~"), "Downloads", "UniversalScraper")
        os.makedirs(self.save_dir, exist_ok=True)

        self.init_ui()
        get_i18n().register_listener(self.update_ui_texts)
        self.update_ui_texts()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. 顶部 OmniFinder 极速接入控制台
        self.omni_group = QGroupBox()
        self.omni_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2196F3;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 14px;
                background-color: #f8faff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 5px;
                color: #1976D2;
            }
        """)
        omni_layout = QVBoxLayout(self.omni_group)

        input_row = QHBoxLayout()
        self.omni_input = ChineseFriendlyLineEdit()
        self.omni_input.setFixedHeight(38)
        self.omni_input.returnPressed.connect(self.start_universal_action)
        input_row.addWidget(self.omni_input)

        self.btn_omni = QPushButton()
        self.btn_omni.setFixedHeight(38)
        self.btn_omni.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 0 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        self.btn_omni.clicked.connect(self.start_universal_action)
        input_row.addWidget(self.btn_omni)
        omni_layout.addLayout(input_row)

        # 辅助功能与状态选项
        options_row = QHBoxLayout()
        self.force_browser_chk = QCheckBox()
        self.force_browser_chk.setStyleSheet("color: #555; font-size: 12px;")
        options_row.addWidget(self.force_browser_chk)

        self.chk_deep_dive = QCheckBox()
        self.chk_deep_dive.setChecked(True)
        self.chk_deep_dive.setStyleSheet("color: #0277BD; font-weight: bold; font-size: 12px; margin-left: 12px;")
        options_row.addWidget(self.chk_deep_dive)

        options_row.addStretch()

        self.lbl_tip = QLabel()
        self.lbl_tip.setStyleSheet("color: #666; font-size: 12px; font-style: italic;")
        options_row.addWidget(self.lbl_tip)

        # 全局语言即时切换下拉框
        self.lang_label = QLabel()
        self.lang_label.setStyleSheet("color: #333; font-weight: bold; font-size: 12px; margin-left: 12px;")
        options_row.addWidget(self.lang_label)

        self.lang_combo = QComboBox()
        self.lang_combo.setStyleSheet("""
            QComboBox {
                background-color: #ffffff;
                color: #1976D2;
                font-weight: bold;
                border: 1.5px solid #2196F3;
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 12px;
                min-width: 110px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                selection-background-color: #e3f2fd;
                selection-color: #1976D2;
            }
        """)
        for code_item, name_item in get_i18n().get_supported_languages():
            self.lang_combo.addItem(name_item, code_item)
        curr_code = get_i18n().current_lang
        idx = self.lang_combo.findData(curr_code)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self.on_language_changed)
        options_row.addWidget(self.lang_combo)

        omni_layout.addLayout(options_row)
        main_layout.addWidget(self.omni_group)


        # 2. 中部主体（分类筛选 + 资源表格）
        splitter = QSplitter(Qt.Horizontal)

        # 左侧筛选
        self.filter_group = QGroupBox()
        filter_layout = QVBoxLayout(self.filter_group)

        self.chk_video = QCheckBox()
        self.chk_video.setChecked(True)
        self.chk_video.stateChanged.connect(self.filter_table)
        filter_layout.addWidget(self.chk_video)

        self.chk_novel = QCheckBox()
        self.chk_novel.setChecked(True)
        self.chk_novel.stateChanged.connect(self.filter_table)
        filter_layout.addWidget(self.chk_novel)

        self.chk_software = QCheckBox()
        self.chk_software.setChecked(True)
        self.chk_software.stateChanged.connect(self.filter_table)
        filter_layout.addWidget(self.chk_software)

        self.chk_doc = QCheckBox()
        self.chk_doc.setChecked(True)
        self.chk_doc.stateChanged.connect(self.filter_table)
        filter_layout.addWidget(self.chk_doc)

        self.chk_image = QCheckBox()
        self.chk_image.setChecked(True)
        self.chk_image.stateChanged.connect(self.filter_table)
        filter_layout.addWidget(self.chk_image)

        filter_layout.addStretch()

        self.btn_select_all = QPushButton()
        self.btn_select_all.clicked.connect(self.select_all_items)
        filter_layout.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton()
        self.btn_deselect_all.clicked.connect(self.deselect_all_items)
        filter_layout.addWidget(self.btn_deselect_all)

        splitter.addWidget(self.filter_group)

        # 右侧表格
        self.table_group = QGroupBox()
        table_layout = QVBoxLayout(self.table_group)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        # 优化各列伸缩和最小宽度，坚决防止内容被挤压折叠为竖排或横杠省略号
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 48)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.table.setColumnWidth(2, 130)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.table.setColumnWidth(3, 90)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Interactive)
        self.table.setColumnWidth(4, 210)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Interactive)
        self.table.setColumnWidth(5, 120)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.itemDoubleClicked.connect(self.on_table_double_clicked)
        self.table.itemChanged.connect(self.update_summary_stats)
        table_layout.addWidget(self.table)

        # 表格下方实时统计标签
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #0366d6; font-weight: bold; padding: 4px;")
        table_layout.addWidget(self.stats_label)

        splitter.addWidget(self.table_group)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)

        main_layout.addWidget(splitter, 4)

        # 3. 底部下载与路径设置
        self.bottom_group = QGroupBox()
        bottom_layout = QVBoxLayout(self.bottom_group)

        path_layout = QHBoxLayout()
        self.lbl_save_dir = QLabel()
        path_layout.addWidget(self.lbl_save_dir)
        self.path_display = QLineEdit(self.save_dir)
        self.path_display.setReadOnly(True)
        path_layout.addWidget(self.path_display)

        self.btn_change_path = QPushButton()
        self.btn_change_path.clicked.connect(self.choose_save_dir)
        path_layout.addWidget(self.btn_change_path)

        self.btn_open_folder = QPushButton()
        self.btn_open_folder.clicked.connect(self.open_download_folder)
        path_layout.addWidget(self.btn_open_folder)

        self.btn_start_download = QPushButton()
        self.btn_start_download.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 6px 14px;")
        self.btn_start_download.clicked.connect(self.start_download)
        path_layout.addWidget(self.btn_start_download)

        bottom_layout.addLayout(path_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        bottom_layout.addWidget(self.progress_bar)

        main_layout.addWidget(self.bottom_group)

        # 4. 实时日志区域
        self.log_group = QGroupBox()
        log_layout = QVBoxLayout(self.log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        main_layout.addWidget(self.log_group, 2)

    def on_language_changed(self, index):
        selected_code = self.lang_combo.itemData(index)
        if selected_code:
            get_i18n().set_language(selected_code)

    def update_ui_texts(self):
        """核心全局全方位多语言热切换刷新引擎：0死角无残留同步翻译"""
        self.setWindowTitle(tr("app_title"))
        self.omni_group.setTitle(tr("omni_title"))
        self.omni_input.setPlaceholderText(tr("omni_placeholder"))
        self.btn_omni.setText(tr("btn_omni"))
        self.force_browser_chk.setText(tr("chk_force_browser"))
        self.chk_deep_dive.setText(tr("chk_deep_dive"))
        self.lbl_tip.setText(tr("lbl_tip"))
        self.lang_label.setText(tr("lbl_lang"))

        self.filter_group.setTitle(tr("filter_group"))
        self.chk_video.setText(tr("chk_video"))
        self.chk_novel.setText(tr("chk_novel"))
        self.chk_software.setText(tr("chk_software"))
        self.chk_doc.setText(tr("chk_doc"))
        self.chk_image.setText(tr("chk_image"))
        self.btn_select_all.setText(tr("btn_select_all"))
        self.btn_deselect_all.setText(tr("btn_deselect_all"))

        self.table_group.setTitle(tr("table_group"))
        self.table.setHorizontalHeaderLabels([
            tr("col_check"),
            tr("col_name"),
            tr("col_type"),
            tr("col_size"),
            tr("col_action"),
            tr("col_url")
        ])

        self.bottom_group.setTitle(tr("bottom_group"))
        self.lbl_save_dir.setText(tr("lbl_save_dir"))
        self.btn_change_path.setText(tr("btn_change_dir"))
        self.btn_open_folder.setText(tr("btn_open_dir"))
        self.btn_start_download.setText(tr("btn_start_download"))
        self.log_group.setTitle(tr("log_group"))

        # 刷新表格内部已生成的行文本与统计信息
        self.filter_table()

    def append_log(self, text: str):
        self.log_text.append(text)

    def update_progress(self, val: int):
        self.progress_bar.setValue(val)

    def choose_save_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, tr("dialog_choose_dir"), self.save_dir)
        if dir_path:
            self.save_dir = dir_path
            self.path_display.setText(dir_path)

    def open_download_folder(self):
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir, exist_ok=True)
        open_media_with_system(self.save_dir)

    def start_universal_action(self):
        raw_text = self.omni_input.text().strip()
        if not raw_text:
            QMessageBox.warning(self, tr("msg_tip"), tr("msg_input_empty"))
            return

        self.btn_omni.setEnabled(False)
        self.all_resources = []
        self.table.setRowCount(0)

        # 智能全自动路由决策
        is_url = raw_text.startswith("http://") or raw_text.startswith("https://")
        is_p2p = any(raw_text.lower().startswith(p) for p in ["magnet:", "ed2k://", "thunder://"])

        force_cdp = self.force_browser_chk.isChecked()

        if is_url:
            self.append_log(tr("log_start_url", url=raw_text))
            def run_url_worker():
                engine = SnifferEngine(log_cb=self.signals.log_signal.emit)
                if force_cdp:
                    results = engine.analyze_with_playwright(raw_text)
                else:
                    results = engine.analyze_auto(raw_text)
                self.signals.scan_finished.emit(results)
            threading.Thread(target=run_url_worker, daemon=True).start()

        elif is_p2p:
            self.append_log(tr("log_start_p2p"))
            p2p_item = [{
                "url": raw_text,
                "category": "document",
                "ext": raw_text.split(":")[0],
                "size": 0,
                "label": f"🧲 P2P资源: {raw_text[:40]}...",
                "referer": ""
            }]
            self.signals.scan_finished.emit(p2p_item)

        else:
            self.append_log(tr("log_start_search", keyword=raw_text))
            is_deep = self.chk_deep_dive.isChecked()
            # 获取用户勾选的专有分类（当用户专门勾选小说/文档/软件等单一或特定分类时精准定向）
            cat_hint = None
            active_cats = []
            if self.chk_video.isChecked(): active_cats.append("video")
            if self.chk_novel.isChecked(): active_cats.append("novel")
            if self.chk_software.isChecked(): active_cats.append("software")
            if self.chk_doc.isChecked(): active_cats.append("document")
            if self.chk_image.isChecked(): active_cats.append("image")

            if len(active_cats) == 1:
                cat_hint = active_cats[0]
            elif "novel" in active_cats and "video" not in active_cats and "doc" not in active_cats:
                cat_hint = "novel"

            def run_search_worker():
                searcher = ResourceSearcher(log_cb=self.signals.log_signal.emit)
                results = searcher.search_all(raw_text, deep_dive=is_deep, category_hint=cat_hint)
                self.signals.scan_finished.emit(results)
            threading.Thread(target=run_search_worker, daemon=True).start()

    def on_scan_finished(self, results):
        self.btn_omni.setEnabled(True)
        self.all_resources = results

        # 智能意图与分类聚焦：若用户没有特意单独只勾某类，且检索出的置顶核心资源为“电子小说在线阅读”，智能自动切换左侧筛选聚焦展示小说
        active_cats_count = sum([self.chk_video.isChecked(), self.chk_novel.isChecked(), self.chk_software.isChecked(), self.chk_doc.isChecked(), self.chk_image.isChecked()])
        has_online_novel = any(r.get("category") == "novel" and r.get("sub_category") == "novel_online" for r in results[:3])
        if has_online_novel and active_cats_count > 1:
            # 自动聚焦于小说分类，带来极致智能无缝的阅读体验
            self.chk_video.blockSignals(True)
            self.chk_novel.blockSignals(True)
            self.chk_software.blockSignals(True)
            self.chk_doc.blockSignals(True)
            self.chk_image.blockSignals(True)

            self.chk_novel.setChecked(True)
            self.chk_video.setChecked(False)
            self.chk_software.setChecked(False)
            self.chk_doc.setChecked(False)
            self.chk_image.setChecked(False)

            self.chk_video.blockSignals(False)
            self.chk_novel.blockSignals(False)
            self.chk_software.blockSignals(False)
            self.chk_doc.blockSignals(False)
            self.chk_image.blockSignals(False)

        self.filter_table()
        self.append_log(tr("log_scan_done", count=len(results)))


    def filter_table(self):
        show_video = self.chk_video.isChecked()
        show_novel = self.chk_novel.isChecked()
        show_software = self.chk_software.isChecked()
        show_doc = self.chk_doc.isChecked()
        show_image = self.chk_image.isChecked()

        filtered = []
        for r in self.all_resources:
            cat = r["category"]
            if cat in ["video", "video_stream", "audio"] and show_video:
                filtered.append(r)
            elif cat == "novel" and show_novel:
                filtered.append(r)
            elif cat == "magnet":
                # 磁力BT资源：仅在勾选影视或软件时展示，避免污染纯办公文档与小说在线阅读
                if show_video or show_software:
                    filtered.append(r)
            elif cat == "pan_drive":
                # 网盘转存资源：仅在勾选软件或办公文档时展示
                if show_doc or show_software:
                    filtered.append(r)
            elif cat == "software" and show_software:
                filtered.append(r)
            elif cat in ["document", "archive", "archive_or_doc"] and show_doc:
                filtered.append(r)
            elif cat == "image" and show_image:
                filtered.append(r)

        self.table.blockSignals(True)
        self.table.setRowCount(len(filtered))
        for row, item in enumerate(filtered):
            # 0. 勾选框
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk_item.setCheckState(Qt.Checked)
            chk_item.setData(Qt.UserRole, item)
            self.table.setItem(row, 0, chk_item)

            # 1. 整理好的资源名称
            label_text = item.get("label") or os.path.basename(item["url"])
            clean_name = label_text.replace(".m3u8", "").replace(".mp4", "")
            self.table.setItem(row, 1, QTableWidgetItem(clean_name))

            # 2. 类型说明
            raw_c = item.get("category", "")
            ext_suffix = f" (.{item.get('ext', '')})" if item.get('ext') and raw_c in ['software', 'document'] else ""
            cat_desc = tr(f"cat_{raw_c}") + ext_suffix if f"cat_{raw_c}" in get_i18n().get_all_keys() else tr("cat_other")
            self.table.setItem(row, 2, QTableWidgetItem(cat_desc))

            # 3. 资源大小展示
            size_val = item.get("size", 0)
            is_stream = item["category"] in ["video_stream", "video"]
            size_display = format_size_str(size_val, is_stream=is_stream)
            size_item = QTableWidgetItem(size_display)
            size_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, size_item)

            # 4. 快速操作列（直观的【▶ 立即播放】、【📖 在线阅读】、【☁️ 转存网盘】、【🧲 磁力直通】与【⬇ 下载】）
            btn_container = QWidget()
            btn_container.setMinimumWidth(200)
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)

            btn_style_base = "font-weight: bold; padding: 4px 10px; border-radius: 3px; min-width: 75px; min-height: 24px;"

            if item["category"] in ["video", "video_stream", "audio"]:
                play_btn = QPushButton(tr("btn_play"))
                play_btn.setStyleSheet(f"background-color: #00C853; color: white; {btn_style_base}")
                play_btn.clicked.connect(lambda checked, url=item["url"], t=clean_name, ref=item.get("referer", ""): self.play_item_stream(url, t, ref))
                btn_layout.addWidget(play_btn)
            elif item["category"] == "novel":
                read_btn = QPushButton(tr("btn_read_novel"))
                read_btn.setStyleSheet(f"background-color: #00897B; color: white; {btn_style_base}")
                read_btn.clicked.connect(lambda checked, it=item: self.open_novel_reader(it))
                btn_layout.addWidget(read_btn)

                down_btn = QPushButton(tr("btn_download_novel"))
                down_btn.setStyleSheet(f"background-color: #4CAF50; color: white; {btn_style_base}")
                down_btn.clicked.connect(lambda checked, it=item: self.download_novel_item(it))
                btn_layout.addWidget(down_btn)
            elif item["category"] == "pan_drive":
                pan_btn = QPushButton(tr("btn_pan"))
                pan_btn.setStyleSheet(f"background-color: #7B1FA2; color: white; {btn_style_base}")
                pan_btn.clicked.connect(lambda checked, it=item: self.open_pan_drive_item(it))
                btn_layout.addWidget(pan_btn)
            elif item["category"] == "magnet":
                mag_btn = QPushButton(tr("btn_magnet"))
                mag_btn.setStyleSheet(f"background-color: #E65100; color: white; {btn_style_base}")
                mag_btn.clicked.connect(lambda checked, it=item: self.open_magnet_item(it))
                btn_layout.addWidget(mag_btn)
            else:
                prev_btn = QPushButton(tr("btn_preview"))
                prev_btn.setStyleSheet(f"background-color: #0288D1; color: white; {btn_style_base}")
                prev_btn.clicked.connect(lambda checked, it=item: self.preview_resource_item(it))
                btn_layout.addWidget(prev_btn)

                down_single_btn = QPushButton(tr("btn_download_single"))
                down_single_btn.setStyleSheet(f"background-color: #4CAF50; color: white; {btn_style_base}")
                down_single_btn.clicked.connect(lambda checked, it=item: self.download_single_item(it))
                btn_layout.addWidget(down_single_btn)

            self.table.setCellWidget(row, 4, btn_container)

            # 5. 真实链接
            self.table.setItem(row, 5, QTableWidgetItem(item["url"]))

        self.table.blockSignals(False)
        self.update_summary_stats()

    def update_summary_stats(self):
        """实时统计表格中显示项数量、已勾选数量及总估计大小"""
        total_rows = self.table.rowCount()
        selected_count = 0
        total_bytes = 0

        for row in range(total_rows):
            chk_item = self.table.item(row, 0)
            if chk_item and chk_item.checkState() == Qt.Checked:
                selected_count += 1
                data = chk_item.data(Qt.UserRole)
                if data:
                    sz = data.get("size", 0)
                    if sz > 0:
                        total_bytes += sz
                    elif data.get("category") in ["video", "video_stream"]:
                        total_bytes += 900 * 1024 * 1024

        size_text = format_size_str(total_bytes, is_stream=False)
        self.stats_label.setText(tr("stats_template", total=total_rows, selected=selected_count, size=size_text))

    def play_item_stream(self, stream_url: str, title: str, referer: str = ""):
        """用户点击【▶ 立即播放】或双击视频行：0.01秒弹出播放窗口并开启硬件加速"""
        self.append_log(tr("log_open_player", title=title))
        dialog = EmbeddedPlayerDialog(stream_url, title=title, referer=referer, parent=self)
        dialog.exec_()

    def preview_resource_item(self, item: dict):
        """弹出资源沉浸式预览窗口（大图样张 / 软件信息），确认无误后再一键下载"""
        self.append_log(tr("log_open_preview", title=item.get("label", "")))
        diag = ResourcePreviewDialog(item, parent=self)
        diag.download_requested.connect(self.download_single_item)
        diag.exec_()

    def download_single_item(self, item: dict):
        """单项即时下载"""
        self.table.blockSignals(True)
        # 仅勾选该项并触发下载
        for r in range(self.table.rowCount()):
            it = self.table.item(r, 0)
            if it:
                d = it.data(Qt.UserRole)
                it.setCheckState(Qt.Checked if (d and d.get("url") == item.get("url")) else Qt.Unchecked)
        self.table.blockSignals(False)
        self.start_download()

    def open_pan_drive_item(self, item: dict):
        """打开网盘转存：一键复制链接与提取码，并在浏览器中自动打开网盘页面"""
        url = item.get("url", "")
        pwd = item.get("pwd", "")
        clipboard = QApplication.clipboard()
        copy_text = f"链接: {url}" + (f"\n提取码: {pwd}" if pwd else "")
        clipboard.setText(copy_text)
        self.append_log(f"【网盘转存】已复制网盘链接与提取码: {copy_text}")
        QMessageBox.information(self, tr("pan_copied_title"), tr("pan_copied_msg", url=url, pwd=pwd or "无"))
        QDesktopServices.openUrl(QUrl(url))

    def open_magnet_item(self, item: dict):
        """磁力直通：一键复制 magnet: 链接至剪贴板，并尝试唤醒本机 BT 客户端"""
        url = item.get("url", "")
        clipboard = QApplication.clipboard()
        clipboard.setText(url)
        self.append_log(f"【磁力直通】已复制磁力链接到剪贴板: {url[:60]}...")
        QMessageBox.information(self, tr("magnet_copied_title"), tr("magnet_copied_msg"))
        QDesktopServices.openUrl(QUrl(url))

    def open_novel_reader(self, item: dict):
        """唤醒专用小说原生阅读窗口"""
        self.append_log(f"【小说阅读】正在打开专属极速阅读窗口: 《{item.get('label', '')}》")
        dialog = NovelReaderDialog(item, parent=self)
        dialog.exec_()

    def download_novel_item(self, item: dict):
        """小说全本下载：打开原生阅读器一键批量缓存与导出 TXT，无需网盘与外部跳转"""
        self.open_novel_reader(item)

    def on_table_double_clicked(self, item):
        row = item.row()
        chk_item = self.table.item(row, 0)
        if not chk_item:
            return
        data = chk_item.data(Qt.UserRole)
        if not data:
            return
        if data.get("category") in ["video", "video_stream", "audio"]:
            url = data["url"]
            title = self.table.item(row, 1).text() if self.table.item(row, 1) else "视频"
            referer = data.get("referer", "")
            self.play_item_stream(url, title, referer)
        elif data.get("category") == "novel":
            self.open_novel_reader(data)
        elif data.get("category") == "pan_drive":
            self.open_pan_drive_item(data)
        elif data.get("category") == "magnet":
            self.open_magnet_item(data)
        else:
            self.preview_resource_item(data)


    def select_all_items(self):
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(Qt.Checked)
        self.table.blockSignals(False)
        self.update_summary_stats()

    def deselect_all_items(self):
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(Qt.Unchecked)
        self.table.blockSignals(False)
        self.update_summary_stats()

    def start_download(self):
        selected = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                selected.append(item.data(Qt.UserRole))

        if not selected:
            QMessageBox.information(self, tr("msg_tip"), tr("msg_no_selected"))
            return

        self.btn_start_download.setEnabled(False)
        self.progress_bar.setValue(0)
        default_referer = self.omni_input.text().strip() if self.omni_input.text().strip().startswith("http") else ""
        self.downloaded_video_files = []

        def download_worker():
            dl = Downloader(self.save_dir)
            total = len(selected)
            for idx, res in enumerate(selected, 1):
                url = res["url"]
                cat = res["category"]
                ext = res["ext"]
                label = res.get("label", "")
                item_referer = res.get("referer") or default_referer
                clean_title = label.replace("🎬 ", "").replace(" ", "_")

                if cat == "video_stream" or ext == "m3u8":
                    ok, path = dl.download_m3u8(url, item_referer, clean_title, log_cb=self.signals.log_signal.emit)
                    if ok and path:
                        self.downloaded_video_files.append(path)
                else:
                    ok, path = dl.download_file(url, item_referer, clean_title, ext, log_cb=self.signals.log_signal.emit)

                    if ok and path and cat == "video":
                        self.downloaded_video_files.append(path)

                self.signals.progress_signal.emit(int((idx / total) * 100))

            self.signals.download_finished.emit(self.downloaded_video_files)

        threading.Thread(target=download_worker, daemon=True).start()

    def on_download_finished(self, downloaded_videos):
        self.btn_start_download.setEnabled(True)
        self.progress_bar.setValue(100)
        self.append_log(tr("log_download_done"))

        if downloaded_videos:
            first_vid = downloaded_videos[0]
            play_reply = QMessageBox.question(
                self,
                tr("msg_download_done"),
                tr("msg_download_done_video", file=os.path.basename(first_vid)),
                QMessageBox.Yes | QMessageBox.No
            )
            if play_reply == QMessageBox.Yes:
                open_media_with_system(first_vid)
        else:
            QMessageBox.information(self, tr("msg_success"), tr("msg_download_done_general", dir=self.save_dir))

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(150, self._ensure_input_focus)

    def _ensure_input_focus(self):
        if sys.platform == "darwin":
            try:
                from Cocoa import NSApplication
                NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
            except Exception:
                pass
        self.activateWindow()
        self.raise_()
        self.omni_input.setFocus()


def main():
    # macOS 原生应用策略激活与输入法焦点绑定
    if sys.platform == "darwin":
        try:
            from Cocoa import NSApplication, NSApplicationActivationPolicyRegular
            app_cocoa = NSApplication.sharedApplication()
            app_cocoa.setActivationPolicy_(NSApplicationActivationPolicyRegular)
            app_cocoa.activateIgnoringOtherApps_(True)
        except Exception:
            pass

    # 注入 Chromium 底层参数：彻底解除 CORS 跨域限制与自动播放拦截，开启硬件加速
    sys.argv.extend([
        "--disable-web-security",
        "--allow-running-insecure-content",
        "--autoplay-policy=no-user-gesture-required",
        "--enable-gpu-rasterization"
    ])

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    window.raise_()
    window.activateWindow()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
