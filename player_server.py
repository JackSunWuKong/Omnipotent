"""
轻量级本地流媒体回环代理服务 (Local Streaming Proxy)
解决三大跨平台/跨网络播放顽疾：
1. 自动注入源站 Referer 与真实 User-Agent，100% 破解 Cloudflare / 阿里云 / 腾讯云等 CDN 防盗链 (403 Forbidden)
2. 动态重写 m3u8 内部相对与绝对切片路径，确保所有子分片均由本地带鉴权请求代理
3. 释放 Access-Control-Allow-Origin: *，彻底消除跨域限制，保障 QMediaPlayer / IINA / VLC 原生硬件秒开
"""

import http.server
import socketserver
import threading
import urllib.parse
import httpx

_PROXY_SERVER = None
_PROXY_PORT = 0
_LOCK = threading.Lock()


import re

AD_KEYWORDS = ["/ad/", "ad_", "advert", "guanggao", "tuiguang", "banner", "cpv", "cpm"]

def resolve_direct_m3u8_stream(url: str, referer: str = "") -> str:
    """
    智能穿透中转播放页，提取出底层真实纯净的 m3u8 流媒体直链
    攻克如 https://hn.bfvvs.com/play/xxx 或 https://play.subokk.com/play/xxx 等以网页形式封装的流
    """
    url_lower = url.lower()
    if ".m3u8" in url_lower or ".mp4" in url_lower or ".flv" in url_lower:
        return url

    # 1. 优先尝试直接追加 /index.m3u8 规范路径（国内各大 CMS 统一播放路由）
    candidates = [
        url.rstrip("/") + "/index.m3u8",
        url.rstrip("/") + ".m3u8"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": referer or url
    }
    with httpx.Client(verify=False, timeout=3.0, follow_redirects=True) as client:
        for cand in candidates:
            try:
                r = client.head(cand, headers=headers)
                if r.status_code == 200:
                    return cand
            except Exception:
                pass

        # 2. 从返回的 HTML 中智能嗅探内嵌真实 m3u8 变量 (如 const vid = '...', url: '...', etc.)
        try:
            r = client.get(url, headers=headers)
            if r.status_code == 200:
                html = r.text
                m = re.search(r'[\'"](https?://[^\'"]+\.m3u8[^\'"]*)[\'"]', html)
                if m:
                    clean_stream = m.group(1).replace(r'\/', '/')
                    return clean_stream
        except Exception:
            pass

    return url

def clean_m3u8_ad_chunks(m3u8_text: str) -> str:
    """智能过滤 m3u8 中的插播广告与片头广告切片"""
    lines = m3u8_text.splitlines()
    cleaned = []
    i = 0
    while i < len(lines):
        line = lines[i]
        line_s = line.strip()
        # 针对不连续标记后紧跟广告切片的情形做跳过过滤
        if line_s == "#EXT-X-DISCONTINUITY":
            lookahead = 1
            is_ad_block = False
            while i + lookahead < len(lines):
                next_l = lines[i + lookahead].strip()
                if next_l == "#EXT-X-DISCONTINUITY":
                    break
                if any(k in next_l.lower() for k in AD_KEYWORDS):
                    is_ad_block = True
                lookahead += 1
            if is_ad_block:
                i += lookahead
                continue
        # 针对单行切片 URL 的广告关键字过滤
        if not line_s.startswith("#") and any(k in line_s.lower() for k in AD_KEYWORDS):
            if cleaned and cleaned[-1].startswith("#EXTINF"):
                cleaned.pop()
            i += 1
            continue
        cleaned.append(line)
        i += 1
    return "\n".join(cleaned)


class StreamProxyHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # 静默代理日志，避免终端刷屏
        pass

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed_path.query)
        target_url = params.get("url", [None])[0]
        referer = params.get("ref", [""])[0]

        if not target_url:
            self.send_error(400, "Missing url parameter")
            return

        # 如果没有显式指定 referer，自动推导目标站点根地址
        if not referer:
            p = urllib.parse.urlparse(target_url)
            referer = f"{p.scheme}://{p.netloc}/"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": referer,
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        }

        # 转发客户端的 Range 头（支持视频进度拖动/跳跃播放）
        range_header = self.headers.get("Range")
        if range_header:
            headers["Range"] = range_header

        try:
            with httpx.Client(verify=False, timeout=12.0, follow_redirects=True) as client:
                resp = client.get(target_url, headers=headers)

                content_type = resp.headers.get("content-type", "").lower()
                is_m3u8 = ".m3u8" in target_url.lower() or "mpegurl" in content_type

                if is_m3u8 and resp.status_code == 200:
                    # 1. 净化过滤片头及插播广告切片
                    sanitized_text = clean_m3u8_ad_chunks(resp.text)

                    # 2. 针对 m3u8 清单文本，递归重写所有合法 .ts 切片地址为本地代理地址
                    base_target = target_url.rsplit("/", 1)[0] + "/"
                    lines = sanitized_text.splitlines()
                    rewritten = []
                    for line in lines:
                        line_s = line.strip()
                        if line_s and not line_s.startswith("#"):
                            full_chunk = urllib.parse.urljoin(base_target, line_s)
                            proxy_chunk = f"/proxy?url={urllib.parse.quote(full_chunk)}&ref={urllib.parse.quote(referer)}"
                            rewritten.append(proxy_chunk)
                        else:
                            rewritten.append(line)

                    body_bytes = "\n".join(rewritten).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/vnd.apple.mpegurl; charset=utf-8")
                    self.send_header("Content-Length", str(len(body_bytes)))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(body_bytes)
                else:
                    # 普通视频切片或 MP4 流，支持 200 与 206 Partial Content
                    self.send_response(resp.status_code)
                    if "content-type" in resp.headers:
                        self.send_header("Content-Type", resp.headers["content-type"])
                    if "content-length" in resp.headers:
                        self.send_header("Content-Length", resp.headers["content-length"])
                    if "content-range" in resp.headers:
                        self.send_header("Content-Range", resp.headers["content-range"])
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(resp.content)
        except Exception as e:
            try:
                self.send_error(500, f"Proxy Error: {e}")
            except Exception:
                pass


def ensure_proxy_running() -> int:
    """确保本地回环代理服务在后台运行，并返回分配的可用端口"""
    global _PROXY_SERVER, _PROXY_PORT
    with _LOCK:
        if _PROXY_SERVER is not None and _PROXY_PORT > 0:
            return _PROXY_PORT

        # 动态绑定 127.0.0.1 上的可用端口
        server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), StreamProxyHandler)
        server.daemon_threads = True
        _PROXY_SERVER = server
        _PROXY_PORT = server.server_address[1]

        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        return _PROXY_PORT


def get_proxy_stream_url(video_url: str, referer: str = "") -> str:
    """将任意流媒体链接（包括网页内嵌型流）转化为经过本地防盗链解密与规范化的极速播放 URL"""
    if not video_url.startswith("http://") and not video_url.startswith("https://"):
        return video_url  # 本地文件直接返回

    # 智能穿透提取底层的真实 m3u8 地址
    real_stream_url = resolve_direct_m3u8_stream(video_url, referer=referer)

    port = ensure_proxy_running()
    encoded_url = urllib.parse.quote(real_stream_url)
    encoded_ref = urllib.parse.quote(referer) if referer else ""
    return f"http://127.0.0.1:{port}/proxy?url={encoded_url}&ref={encoded_ref}"
