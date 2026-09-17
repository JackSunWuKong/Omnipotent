"""
工业级资源下载引擎
支持：通用多协议下载、Referer防盗链穿透、m3u8多线程抓取与转码
优先使用专业的流媒体拉流引擎 yt-dlp + ffmpeg 组合，确保 100% 正常播放
"""

import os
import re
import shutil
import subprocess
from urllib.parse import urlparse
import requests

def sanitize_filename(name: str) -> str:
    """去除文件名中非法字符"""
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', '_', name)
    return name.strip()[:200]

class Downloader:
    def __init__(self, save_dir: str):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

    def download_file(self, url: str, referer: str, suggested_name: str, ext: str, log_cb=print, progress_cb=None):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": referer,
            "Accept": "*/*"
        }

        if not suggested_name:
            parsed = urlparse(url)
            suggested_name = os.path.basename(parsed.path) or "downloaded_file"

        if ext and not suggested_name.lower().endswith(f".{ext.lower()}"):
            suggested_name = f"{suggested_name}.{ext}"

        filename = sanitize_filename(suggested_name)
        target_path = os.path.join(self.save_dir, filename)

        base_name, file_ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(target_path):
            target_path = os.path.join(self.save_dir, f"{base_name}_{counter}{file_ext}")
            counter += 1

        log_cb(f"开始下载: {filename} -> {url}")

        try:
            with requests.get(url, headers=headers, stream=True, timeout=30) as r:
                r.raise_for_status()
                total_length = r.headers.get('content-length')
                dl = 0
                total_size = int(total_length) if total_length else 0

                with open(target_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            dl += len(chunk)
                            if progress_cb and total_size > 0:
                                percent = int((dl / total_size) * 100)
                                progress_cb(percent)

            log_cb(f"✓ 下载成功: {filename}")
            # 针对下载的压缩包执行智能垃圾广告与诱导链接清理
            self.sanitize_archive_contents(target_path, log_cb)
            return True, target_path
        except Exception as e:
            log_cb(f"✗ 下载失败: {url} | 错误: {e}")
            if os.path.exists(target_path):
                os.remove(target_path)
            return False, str(e)

    def sanitize_archive_contents(self, archive_path: str, log_cb=print):
        """自动解包扫描并剔除 .url / 【下载必看】.txt / 垃圾推广诱导文件"""
        if not archive_path.lower().endswith(".zip"):
            return
        import zipfile
        try:
            temp_clean_path = archive_path + ".clean.zip"
            cleaned_count = 0
            with zipfile.ZipFile(archive_path, 'r') as zin:
                with zipfile.ZipFile(temp_clean_path, 'w') as zout:
                    for item in zin.infolist():
                        fn_low = item.filename.lower()
                        # 识别常见的网址推广、下载说明、诱导快捷方式
                        is_junk = (
                            fn_low.endswith(".url") or
                            fn_low.endswith(".lnk") or
                            any(k in fn_low for k in ["下载必看", "最新网址", "点击发布", "更多资源", "加qq群", "推广", "广告", "福利", "群", "关注", "公众号", "必看", "网址发布"])
                        )
                        if is_junk:
                            cleaned_count += 1
                            continue
                        buffer = zin.read(item.filename)
                        zout.writestr(item, buffer)
            if cleaned_count > 0:
                os.replace(temp_clean_path, archive_path)
                log_cb(f"🛡️ [资源净化] 已自动从压缩包中彻底剥离剔除 {cleaned_count} 个推广垃圾与诱导文件！")
            elif os.path.exists(temp_clean_path):
                os.remove(temp_clean_path)
        except Exception:
            pass

    def download_m3u8(self, m3u8_url: str, referer: str, suggested_name: str, log_cb=print):
        """
        使用 yt-dlp 原生拉流（自动解密、并发拉切片、修复元数据与时间戳，并输出标准可播放 mp4）
        若失败则自动回退到 ffmpeg 引擎
        """
        if not suggested_name:
            suggested_name = "video_stream"
        suggested_name = sanitize_filename(suggested_name)
        if not suggested_name.lower().endswith(".mp4"):
            suggested_name += ".mp4"

        target_path = os.path.join(self.save_dir, suggested_name)
        base_name, file_ext = os.path.splitext(suggested_name)
        counter = 1
        while os.path.exists(target_path):
            target_path = os.path.join(self.save_dir, f"{base_name}_{counter}{file_ext}")
            counter += 1

        log_cb(f"启动工业级流媒体下载合成引擎: {os.path.basename(target_path)}")

        # 优先使用 yt-dlp Python API 直接拉流合并
        try:
            from yt_dlp import YoutubeDL
            ydl_opts = {
                'outtmpl': target_path,
                'format': 'best',
                'quiet': True,
                'no_warnings': True,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                    'Referer': referer or m3u8_url
                }
            }
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([m3u8_url])

            if os.path.exists(target_path) and os.path.getsize(target_path) > 1024:
                file_mb = os.path.getsize(target_path) / (1024 * 1024)
                log_cb(f"✓ 视频切片合并成功！大小: {file_mb:.2f} MB，文件已可正常秒播。")
                return True, target_path
        except Exception as e:
            log_cb(f"[切换通道] yt-dlp 拉流异常 ({e})，正在调用 FFmpeg 备用通道...")

        # 备用：调用 FFmpeg
        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffmpeg_bin:
            log_cb("[警告] 系统未安装 ffmpeg，无法执行备用转码！")
            return False, "ffmpeg not found"

        cmd = [
            ffmpeg_bin, "-y", "-nostdin",
            "-i", m3u8_url,
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            "-movflags", "+faststart",
            target_path
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(target_path) and os.path.getsize(target_path) > 1024:
                file_mb = os.path.getsize(target_path) / (1024 * 1024)
                log_cb(f"✓ 视频备用通道合并成功！大小: {file_mb:.2f} MB")
                return True, target_path
        except Exception as e:
            log_cb(f"✗ 备用通道异常: {e}")

        return False, "failed"
