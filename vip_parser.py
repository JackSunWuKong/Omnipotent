"""
影视全网解析接口调度模块（聚合主流影视解析线路）
专门解决腾讯视频、爱奇艺、优酷等平台的专属算法加密/外星人劫持问题
将长视频页面一键转换为可提取的 m3u8 / mp4 真实直链
"""

import re
import httpx

# 聚合业内常用稳定的全网影视解析线路
VIP_ROUTES = [
    ("虾米解析", "https://jx.xmflv.cc/?url="),
    ("json解析", "https://jx.jsonplayer.com/player/?url="),
    ("M3U8解析", "https://jx.m3u8.tv/jiexi/?url="),
    ("阳途解析", "https://jx.yangtu.top/?url=")
]

def parse_vip_video_stream(target_url: str, log_cb=print):
    """
    输入腾讯/爱奇艺等平台的播放页 URL，调用穿透接口解析出背后的 m3u8 清单或 mp4 直链
    """
    log_cb(f"检测到主流影视加密平台链接，正在启动全网影视智能穿透模块...")
    results = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": target_url
    }

    client = httpx.Client(headers=headers, timeout=8.0, verify=False, follow_redirects=True)

    for route_name, api_prefix in VIP_ROUTES:
        full_api = f"{api_prefix}{target_url}"
        log_cb(f"正在尝试使用 [{route_name}] 线路穿透分析...")
        try:
            resp = client.get(full_api)
            html = resp.text

            # 1. 扫描返回页面中内嵌的 url= 或 m3u8 变量
            # 例如: "url": "https://.../index.m3u8", "src": "..."
            m3u8_matches = re.findall(r'https?[:\\/]+[^\s"\'<>]+\.m3u8[^\s"\'<>]*', html, re.IGNORECASE)
            mp4_matches = re.findall(r'https?[:\\/]+[^\s"\'<>]+\.mp4[^\s"\'<>]*', html, re.IGNORECASE)

            for m in m3u8_matches + mp4_matches:
                clean_url = m.replace(r'\/', '/')
                # 修复可能存在的双斜杠
                clean_url = re.sub(r'([^:])//+', r'\1/', clean_url)
                if clean_url.startswith("http"):
                    is_m3u8 = ".m3u8" in clean_url.lower()
                    results.append({
                        "url": clean_url,
                        "category": "video_stream" if is_m3u8 else "video",
                        "ext": "m3u8" if is_m3u8 else "mp4",
                        "size": 0,
                        "label": f"🎬 [影视穿透线路] {route_name} - {'m3u8高清流' if is_m3u8 else 'mp4直链'}"
                    })

            if results:
                log_cb(f"✓ [{route_name}] 线路穿透成功！捕获到真实流媒体地址。")
                break
        except Exception:
            continue

    return results
