"""
工业级流媒体与视频解析核心
集成 yt-dlp 专属解析器，自动穿透腾讯视频、Bilibili、优酷、爱奇艺、YouTube 等平台的私有签名、分片与清晰度
"""

import os
from yt_dlp import YoutubeDL

class VideoExtractor:
    def __init__(self, log_cb=print):
        self.log_cb = log_cb

    def extract_video_info(self, url: str):
        """
        深度提取视频真实流信息：
        支持提取标题、分辨率、视频流地址、格式
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': False,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Referer': url
            }
        }

        self.log_cb(f"正在调用工业级视频逆向引擎分析媒体流: {url}")
        results = []

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return results

                # 如果是播放列表/合集
                entries = info.get('entries') if 'entries' in info else [info]

                for entry in entries:
                    if not entry:
                        continue
                    title = entry.get('title') or '在线影视视频'
                    formats = entry.get('formats') or []
                    
                    # 如果没有直接的 formats，直接提取 url
                    if not formats and entry.get('url'):
                        results.append({
                            "url": entry['url'],
                            "category": "video",
                            "ext": entry.get('ext') or 'mp4',
                            "size": entry.get('filesize') or 0,
                            "label": f"🎬 {title}"
                        })
                        continue

                    # 挑选最佳画质或所有可用清晰度
                    # 倒序遍历（通常后面的画质更高）
                    added_qualities = set()
                    for f in reversed(formats):
                        f_url = f.get('url')
                        if not f_url:
                            continue
                        resolution = f.get('format_note') or f.get('resolution') or f.get('format') or '高清'
                        if resolution in added_qualities:
                            continue
                        added_qualities.add(resolution)

                        ext = f.get('ext') or 'mp4'
                        size = f.get('filesize') or f.get('filesize_approx') or 0
                        is_m3u8 = 'm3u8' in f_url or ext == 'm3u8'

                        results.append({
                            "url": f_url,
                            "category": "video_stream" if is_m3u8 else "video",
                            "ext": "m3u8" if is_m3u8 else ext,
                            "size": size,
                            "label": f"🎬 {title} [{resolution}]"
                        })
                        # 只取前 3 个最高画质档位，避免列表冗余
                        if len(added_qualities) >= 3:
                            break

            self.log_cb(f"视频解析引擎捕获成功！提取到 {len(results)} 条高清视频流。")
        except Exception as e:
            self.log_cb(f"[视频解析引擎提示] {e}")

        return results
