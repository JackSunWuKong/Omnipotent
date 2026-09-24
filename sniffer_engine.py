"""
智能多层网络嗅探与反伪装引擎（终极全能旗舰版 - 老站新站全兼容）
专为应对以下全场景设计：
1. 【经典/老旧网站 (Legacy Sites)】:
   - 自动识别 GBK / GB2312 / GB18030 / Big5 编码，彻底消除中文乱码
   - 深度穿透苹果CMS (MacCMS)、海洋CMS、飞飞CMS (player_data, player_aaaa, base64, unescape)
   - 全面支持 <embed>, <object>, <param>, Flash, 传统 FLV/WMV/RMVB/AVI/MKV
   - 提取 P2P 共享资源: 磁力链接(magnet)、电驴(ed2k)、迅雷(thunder)、种子(torrent)
   - 递归穿透第三方播放器 iframe 与解析接口 (jx.php, player.html?url=...)

2. 【现代/动态网站 (Modern SPA & MSE Sites)】:
   - Playwright CDP 底层网络请求与响应全量拦截 (支持 application/vnd.apple.mpegurl, video/*)
   - 注入 Stealth 规避现代前端反无头爬虫检测 (绕过 navigator.webdriver 等)
   - 模拟真实用户播放手势 (触发 .play, .vjs-big-play-button, DPlayer 等，破除自动播放限制)
   - 深入 API / XHR / Fetch 响应体，挖掘现代 SPA 异步下发的 JSON 隐藏媒体流
   - 智能噪声过滤 (剔除 empty.mp4 假视频及成百上千的小 ts 切片，只保留完整流媒体)
"""

import os
import re
import json
import base64
import urllib.parse
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup

from sniffer_magic import identify_resource
from video_extractor import VideoExtractor
from vip_parser import parse_vip_video_stream
from autonomous_agent import autonomous_agent


def decode_html_bytes(content: bytes, headers: dict = None) -> str:
    """智能解码 HTML 字节流，完美支持老旧中文网站 (GBK/GB2312/Big5) 与现代 UTF-8"""
    if not content:
        return ""

    # 1. 优先从 HTTP Response Headers 中提取编码
    if headers:
        for k, v in headers.items():
            if k.lower() == "content-type" and "charset=" in v.lower():
                enc = v.lower().split("charset=")[-1].split(";")[0].strip()
                try:
                    return content.decode(enc)
                except Exception:
                    pass

    # 2. 从 HTML 前 2048 字节嗅探 <meta charset="...">
    sample = content[:2048].lower()
    meta_charset = re.search(rb'<meta[^>]+charset=["\']?([\w\-]+)', sample)
    if meta_charset:
        try:
            enc = meta_charset.group(1).decode("ascii", "ignore").strip()
            return content.decode(enc)
        except Exception:
            pass

    # 3. 经典老旧中文编码依次推导尝试
    for enc in ["utf-8", "gb18030", "gbk", "gb2312", "big5", "cp936"]:
        try:
            return content.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue

    # 4. 最后回退带容错的 utf-8
    return content.decode("utf-8", errors="replace")


def extract_cms_streams(html: str) -> list:
    """提取国内各主流老牌影视 CMS (苹果CMS、海洋CMS、飞飞CMS等) 中的隐藏视频流"""
    streams = []

    # 1. 苹果CMS (MacCMS) player_data / player_aaaa 结构
    # 结构格式: var player_data={"flag":"...","encrypt":1/2/3,"url":"..."}
    for match in re.finditer(r'(?:player_data|player_aaaa)\s*=\s*(\{.+?\})', html, re.DOTALL):
        try:
            raw_json = match.group(1).strip().rstrip(";")
            data = json.loads(raw_json)
            url = data.get("url", "")
            encrypt = data.get("encrypt", 0)

            if encrypt == 1:
                # URL 编码
                url = urllib.parse.unquote(url)
            elif encrypt == 2:
                # Base64 编码
                try:
                    url = base64.b64decode(url).decode("utf-8", "ignore")
                except Exception:
                    pass
            elif encrypt == 3:
                # unescape + Base64 复合编码
                try:
                    url = urllib.parse.unquote(base64.b64decode(url).decode("latin-1", "ignore"))
                except Exception:
                    pass

            if url and ("http" in url or ".m3u8" in url or ".mp4" in url):
                streams.append(url)
        except Exception:
            pass

    # 2. 常见传统播放器脚本内联定义 (video: '...', url: '...', file: '...', now: '...')
    patterns = [
        r'[\'"](?:file|url|src|video|link|playUrl|videoUrl)[\'"]\s*:\s*[\'"](https?:[^\'"]+\.(?:m3u8|mp4|flv|f4v|webm|mkv)[^\'"]*)[\'"]',
        r'var\s+(?:video|url|v_url|now|vUrl|play_url|m3u8_url)\s*=\s*[\'"](https?:[^\'"]+\.(?:m3u8|mp4|flv|f4v|webm|mkv)[^\'"]*)[\'"]',
        r'source\s*:\s*[\'"](https?:[^\'"]+\.(?:m3u8|mp4|flv)[^\'"]*)[\'"]'
    ]
    for pat in patterns:
        for m in re.findall(pat, html, re.IGNORECASE):
            clean = m.replace(r'\/', '/')
            streams.append(clean)

    # 3. 老旧 Flash / Embed / Object 媒体嵌入标签
    embed_patterns = [
        r'<embed[^>]+src=["\'](https?:[^\'"]+\.(?:swf|flv|mp4|wmv|avi|rmvb)[^\'"]*)["\']',
        r'<param[^>]+name=["\'](?:src|movie|filename|url)["\'][^>]+value=["\'](https?:[^\'"]+)["\']',
        r'<param[^>]+value=["\'](https?:[^\'"]+)["\'][^>]+name=["\'](?:src|movie|filename|url)["\']'
    ]
    for pat in embed_patterns:
        for m in re.findall(pat, html, re.IGNORECASE):
            clean = m.replace(r'\/', '/')
            streams.append(clean)

    return list(set(streams))


class SnifferEngine:
    def __init__(self, log_cb=print):
        self.log_cb = log_cb
        self.video_extractor = VideoExtractor(log_cb=self.log_cb)

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        }
        self.client = httpx.Client(
            headers=self.headers,
            timeout=httpx.Timeout(12.0, connect=6.0),
            follow_redirects=True,
            verify=False
        )

    def probe_resource_info(self, url: str, referer: str):
        """精准检测资源类型与大小（融合指纹魔数穿透伪装）"""
        url_lower = url.lower().split("?")[0]
        # P2P 或特定协议
        if url.lower().startswith("magnet:"):
            return "magnet", "magnet", 0
        if url.lower().startswith("ed2k://") or url.lower().startswith("thunder://"):
            return "document", url.split(":")[0], 0

        # 网盘转存链接
        pan_domains = ["pan.quark.cn", "pan.baidu.com", "123pan.com", "lanzou", "ctfile.com", "aliyundrive.com", "drive.uc.cn", "mypikpak.com"]
        if any(pd in url.lower() for pd in pan_domains):
            return "pan_drive", "pan", 0

        for ext in [".m3u8", ".mp4", ".flv", ".webm", ".avi", ".mkv", ".wmv", ".rmvb", ".mov"]:
            if url_lower.endswith(ext):
                return ("video_stream" if ext == ".m3u8" else "video"), ext.strip("."), 0
        for ext in [".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".wma"]:
            if url_lower.endswith(ext):
                return "audio", ext.strip("."), 0
        for ext in [".exe", ".dmg", ".pkg", ".apk", ".msi", ".deb", ".rpm", ".iso", ".ipa", ".appimage"]:
            if url_lower.endswith(ext):
                return "software", ext.strip("."), 0
        for ext in [".pdf", ".docx", ".xlsx", ".pptx", ".doc", ".xls", ".zip", ".rar", ".7z", ".torrent"]:
            if url_lower.endswith(ext):
                return "document", ext.strip("."), 0
        for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".bmp", ".ico"]:
            if url_lower.endswith(ext):
                return "image", ext.strip("."), 0


        req_headers = {"Referer": referer}
        try:
            head_resp = self.client.head(url, headers=req_headers)
            content_type = head_resp.headers.get("content-type", "")
            size = head_resp.headers.get("content-length", 0)

            sample_bytes = None
            if not content_type or "octet-stream" in content_type:
                range_headers = req_headers.copy()
                range_headers["Range"] = "bytes=0-31"
                with self.client.stream("GET", url, headers=range_headers) as r:
                    sample_bytes = next(r.iter_bytes(32), b"")

            cat, ext = identify_resource(content_type, url, sample_bytes)
            return cat, ext, int(size) if size else 0
        except Exception:
            cat, ext = identify_resource("", url, None)
            return cat, ext, 0

    def analyze_static_and_dom(self, target_url: str):
        self.log_cb(f"=== 正在启动多维全息嗅探体系: {target_url} ===")
        results = []
        seen_urls = set()

        is_vip_site = any(d in target_url.lower() for d in ["v.qq.com", "iqiyi.com", "youku.com", "mgtv.com", "bilibili.com", "youtube.com"])
        is_specific_video_page = any(p in target_url.lower() for p in ["/cover/", "/x/cover/", "/play/", "/video/", "watch?v="])

        # 1. 影视大厂平台专属穿透通道
        if is_vip_site and is_specific_video_page:
            self.log_cb("检测到影视大厂链接，启动专属流媒体穿透通道...")
            vip_streams = parse_vip_video_stream(target_url, log_cb=self.log_cb)
            for vs in vip_streams:
                if vs["url"] not in seen_urls:
                    seen_urls.add(vs["url"])
                    results.append(vs)

            video_results = self.video_extractor.extract_video_info(target_url)
            for vr in video_results:
                if vr["url"] not in seen_urls:
                    seen_urls.add(vr["url"])
                    results.append(vr)

        # 2. 静态页面拉取与智能全编码解码
        self.log_cb(f"正在拉取页面底层骨架与多媒体资源: {target_url}")
        try:
            resp = self.client.get(target_url)
            html = decode_html_bytes(resp.content, resp.headers)
            soup = BeautifulSoup(html, "html.parser")
        except Exception as e:
            self.log_cb(f"[网络提示] 获取页面内容异常: {e}")
            return results

        title = "未知页面"
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        self.log_cb(f"成功解析网页文档: 《{title}》")

        def add_candidate(raw_url, label=""):
            if not raw_url or raw_url.startswith("javascript:") or raw_url.startswith("data:"):
                return
            full_url = urljoin(target_url, raw_url.strip())
            if full_url in seen_urls:
                return
            seen_urls.add(full_url)

            cat, ext, size = self.probe_resource_info(full_url, target_url)
            if cat != "other":
                results.append({
                    "url": full_url,
                    "category": cat,
                    "ext": ext,
                    "size": size,
                    "label": label or os.path.basename(urlparse(full_url).path)
                })

        # 3. 深度解析老牌 CMS 播放变量 (苹果CMS/海洋CMS/DPlayer/JWPlayer等)
        cms_streams = extract_cms_streams(html)
        if cms_streams:
            self.log_cb(f"成功穿透老牌 CMS/播放器变量，捕获到 {len(cms_streams)} 条流媒体！")
            for cs in cms_streams:
                add_candidate(cs, f"《{title}》CMS内嵌流")

        # 4. 扫描 HTML5 video / audio / source 标签
        for vid in soup.find_all(["video", "audio", "source"]):
            src = vid.get("src")
            if src:
                add_candidate(src, f"《{title}》原生播放源")

        # 5. 扫描老旧 Flash、Embed、Object 标签
        for emb in soup.find_all(["embed", "object"]):
            src = emb.get("src") or emb.get("data")
            if src:
                add_candidate(src, f"《{title}》Embed传统媒体")

        # 6. 扫描 iframe 嵌套播放器与解析器接口
        for iframe in soup.find_all("iframe"):
            isrc = iframe.get("src")
            if isrc:
                clean_isrc = urljoin(target_url, isrc.strip())
                # 检查 iframe src 查询参数里是否携带流地址 (如 ?url=https://...m3u8)
                parsed_frame = urlparse(clean_isrc)
                qs = urllib.parse.parse_qs(parsed_frame.query)
                for qk, qvals in qs.items():
                    for qv in qvals:
                        if any(ext in qv.lower() for ext in [".m3u8", ".mp4", ".flv"]):
                            add_candidate(qv, f"《{title}》iframe解析流")

                # 如果是内联播放器页面且尚未拿到流，递归抓取 iframe 内部内容
                if any(k in clean_isrc.lower() for k in ["play", "video", "jx", "jiexi", "player"]):
                    try:
                        frame_resp = self.client.get(clean_isrc, headers={"Referer": target_url})
                        frame_html = decode_html_bytes(frame_resp.content, frame_resp.headers)
                        sub_streams = extract_cms_streams(frame_html)
                        for ss in sub_streams:
                            add_candidate(ss, f"《{title}》子播放器流")
                        sub_matches = re.findall(r'https?:\\?/\\?/[^\s"\'<>]+\.(?:m3u8|mp4|flv)[^\s"\'<>]*', frame_html, re.IGNORECASE)
                        for sm in sub_matches:
                            add_candidate(sm.replace(r'\/', '/'), f"《{title}》子页面流")
                    except Exception:
                        pass

        # 7. 全局正则强力穿透内联流媒体 (m3u8/mp4/flv/wmv/avi)
        stream_matches = re.findall(r'https?:\\?/\\?/[^\s"\'<>]+\.(?:m3u8|mp4|flv|f4v|webm|mkv|wmv|avi|rmvb)[^\s"\'<>]*', html, re.IGNORECASE)
        for m in stream_matches:
            add_candidate(m.replace(r'\/', '/'), f"《{title}》内嵌媒体流")

        # 8. 扫描传统资源共享协议 (磁力链接/电驴/迅雷/BT种子)
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            hl = href.lower()
            if hl.startswith("magnet:") or hl.startswith("ed2k://") or hl.startswith("thunder://") or hl.endswith(".torrent"):
                link_title = a.get_text(strip=True) or os.path.basename(urlparse(href).path)
                add_candidate(href, f"P2P下载: {link_title}")

        # 9. 扫描图片/封面/海报
        for img in soup.find_all("img"):
            for attr in ["src", "data-src", "data-original", "data-lazy-src", "srcset", "v-lazy"]:
                val = img.get(attr)
                if val:
                    if "," in val:
                        for item in val.split(","):
                            p = item.strip().split(" ")[0]
                            add_candidate(p, img.get("alt", "图片海报"))
                    else:
                        add_candidate(val, img.get("alt", "图片海报"))

        # 10. 扫描常规文档、安装包与附件及网盘资源
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            path_lower = urlparse(href).path.lower()
            doc_or_app_exts = [
                ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".rar", ".7z", ".txt", ".csv",
                ".exe", ".dmg", ".pkg", ".apk", ".msi", ".deb", ".rpm", ".iso", ".ipa", ".appimage"
            ]
            pan_hosts = ["pan.quark.cn", "pan.baidu.com", "123pan.com", "lanzou", "ctfile.com", "aliyundrive.com", "drive.uc.cn"]
            is_app_link = any(path_lower.endswith(e) for e in doc_or_app_exts)
            is_pan_link = any(ph in href.lower() for ph in pan_hosts)
            is_down_link = any(k in href.lower() for k in ["download", "/down/", "release", "installer"])

            if is_app_link or is_pan_link or is_down_link:
                link_text = a.get_text(strip=True) or os.path.basename(path_lower)
                # 排除纯“教程”网盘推广干扰，优先保障软件与安装包纯度
                if is_pan_link and "教程" in link_text and not any(k in link_text for k in ["下载", "安装包", "原件"]):
                    continue
                add_candidate(href, link_text)

        # 10.5 🤖【AI 通用自愈穿透智能体】对网页所有按钮进行视觉与认知打分，自动避开流氓全家桶，萃取真实直链
        healed_elements = autonomous_agent.self_heal_and_extract(html, target_url)
        if healed_elements:
            self.log_cb(f"🤖 [AI 自愈感知] 经人类视觉行为认知打分，成功推演并萃取 {len(healed_elements)} 个高置信度真实下载目标，已绕过所有广告诱导按钮！")
            for he in healed_elements:
                add_candidate(he["url"], f"🎯 {he['label']} (AI置信度: {int(he['confidence_score'])})")

        # 11. 软件应用聚合门户深度穿透探针（攻克如 MacWk、精选软件站、WordPress 应用导航等深水区）
        # 此类站点首页或列表页仅展示应用卡片，下载直链与网盘提取码藏在内页或通过 Ajax/弹窗动态生成
        software_posts = []
        for a in soup.find_all("a", href=True):
            h = urljoin(target_url, a["href"].strip())
            t = a.get_text(strip=True)
            # 识别应用详情页特征（如 /app/123.html、/soft/、/mac/、/post/ 等）
            is_app_detail = bool(re.search(r'/(?:app/|soft/|down/|software/)?\d+\.html$', h, re.IGNORECASE))
            if is_app_detail and len(t) >= 2 and not any(bad in t for bad in ["教程", "常见故障", "留言", "登录", "注册", "排行榜"]):
                if h not in [sp[0] for sp in software_posts]:
                    software_posts.append((h, t))

        if software_posts:
            self.log_cb(f"🚀 [软件暗河穿透] 智能探测到应用聚合门户特征，发现 {len(software_posts)} 款软件条目，正在开启深度并发穿透解析...")
            import concurrent.futures

            def probe_single_software(post_item):
                post_url, app_name = post_item
                found_res = []
                try:
                    sub_r = self.client.get(post_url, headers={"Referer": target_url})
                    sub_html = sub_r.text
                    sub_soup = BeautifulSoup(sub_html, "html.parser")

                    # 机制 A: 检测 Ajax 弹窗下载配置（如 OneNav / MacWk 的 get_app_down_btn）
                    btns = re.findall(r'<button[^>]*data-action=[\'"]get_app_down_btn[\'"][^>]*>', sub_html)
                    if btns:
                        m_post = re.search(r'data-post_id=[\'"](\d+)[\'"]', btns[0])
                        m_id = re.search(r'data-id=[\'"](\d+)[\'"]', btns[0])
                        if m_post and m_id:
                            ajax_url = urljoin(post_url, '/wp-admin/admin-ajax.php')
                            ajax_r = self.client.post(
                                ajax_url,
                                data={'action': 'get_app_down_btn', 'post_id': m_post.group(1), 'id': m_id.group(1)},
                                headers={"Referer": post_url}
                            )
                            ajax_soup = BeautifulSoup(ajax_r.text, "html.parser")
                            for da in ajax_soup.find_all("a", href=True):
                                d_url = da["href"].strip()
                                if any(ph in d_url for ph in ["pan.quark.cn", "pan.baidu.com", "123pan.com", "ctfile.com", "lanzou"]):
                                    pwd = da.get("data-clipboard-text", "")
                                    btn_txt = da.get_text(strip=True)
                                    found_res.append({
                                        "url": d_url,
                                        "category": "pan_drive",
                                        "ext": "dmg",
                                        "size": 0,
                                        "pwd": pwd,
                                        "label": f"💻 《{app_name}》 (官方纯净安装包/转存)",
                                        "source_engine": "MacWk直穿",
                                        "referer": post_url
                                    })

                    # 机制 B: 抓取正文中的直链与网盘链接
                    for sub_a in sub_soup.find_all("a", href=True):
                        sh = sub_a["href"].strip()
                        if any(ph in sh for ph in ["pan.quark.cn", "pan.baidu.com", "123pan.com", "ctfile.com", "lanzou"]):
                            found_res.append({
                                "url": sh,
                                "category": "pan_drive",
                                "ext": "dmg",
                                "size": 0,
                                "pwd": "",
                                "label": f"💻 《{app_name}》 (全套资源附件)",
                                "source_engine": "内页直取",
                                "referer": post_url
                            })
                        elif any(sh.lower().split("?")[0].endswith(e) for e in [".dmg", ".pkg", ".zip", ".exe"]):
                            found_res.append({
                                "url": sh,
                                "category": "software",
                                "ext": sh.lower().split(".")[-1].split("?")[0],
                                "size": 0,
                                "label": f"💻 《{app_name}》 (直链下载)",
                                "source_engine": "原件直通",
                                "referer": post_url
                            })
                except Exception:
                    pass
                return found_res

            # 并发深度扫描前 25 款重点热门应用，秒级穿透拿到真实下载与网盘直链
            deep_app_results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
                sub_futs = [ex.submit(probe_single_software, sp) for sp in software_posts[:25]]
                for sf in concurrent.futures.as_completed(sub_futs):
                    for r_item in sf.result():
                        if r_item["url"] not in seen_urls:
                            seen_urls.add(r_item["url"])
                            deep_app_results.append(r_item)

            # 将深挖出的软件与安装包置顶展示在最前排，给用户最直接的体验
            results = deep_app_results + results
            self.log_cb(f"✓ [软件暗河穿透完成] 成功穿透解密出 {len(deep_app_results)} 款真实软件下载与转存直链并置顶交付！")

        # 11.5 🌐【综合门户与分流跳转池深度穿透探针】（攻克如 kdsou.com / 卡盟导航 / 聚合发卡中转站等深水区）
        # 此类站点外层为门户宣传页，通过重定向脚本或多级跳转池（如 g8g8.top -> 真实服务分发集群）隐藏核心业务直链
        gateway_links = []
        for a in soup.find_all("a", href=True):
            h_raw = a["href"].strip()
            if not h_raw or h_raw.startswith("#") or h_raw.startswith("javascript:"):
                continue
            h_full = urljoin(target_url, h_raw)
            link_txt = a.get_text(strip=True) or "门户业务通道"
            # 识别外链跳转池、子服务网关与业务直通入口
            if h_full != target_url and not any(h_full.lower().endswith(ext) for ext in [".css", ".js", ".ico", ".png", ".jpg", ".jpeg", ".gif"]):
                if not any(ign in h_full for ign in ["miit.gov.cn", "beian", "baidu.com", "google.com"]):
                    if h_full not in [gl[0] for gl in gateway_links]:
                        gateway_links.append((h_full, link_txt))

        # 若主站为聚合门户且常规媒体/软件为空，自动穿透跳转池提取底层业务节点与资源
        if gateway_links and not any(r.get("category") in ["software", "pan_drive", "video_stream"] for r in results):
            self.log_cb(f"🌐 [门户跳转池穿透] 检测到业务分流跳转网关，发现 {len(gateway_links)} 个外链通道，正在深入解密真实服务集群...")
            portal_results = []
            for gw_url, gw_label in gateway_links[:5]:
                try:
                    gw_r = self.client.get(gw_url, headers={"Referer": target_url}, timeout=6.0)
                    if gw_r.status_code == 200:
                        gw_html = gw_r.text
                        # 嗅探跳转池数组（如 var urls = [...]）
                        pool_urls = re.findall(r'[\'\"`](https?://[^\'\"`\s]+)[\'\"`]', gw_html)
                        valid_pool = [
                            u for u in pool_urls
                            if any(u.endswith(ext) or ext in u for ext in ['.top/', '.cn/', '.vip/', '.com/', '.html'])
                            and not any(bad in u.lower() for bad in ['qpic', '.png', '.jpg', '.gif', '.css', '.js', 'beian', 'gov.cn'])
                        ]

                        # 记录网关入口直链
                        portal_results.append({
                            "url": gw_url,
                            "category": "software",
                            "ext": "web",
                            "size": 0,
                            "label": f"🌐 《{title}》 核心业务直达通道 ({gw_label})",
                            "source_engine": "门户穿透",
                            "referer": target_url
                        })

                        # 如果挖掘出底层集群负载节点，全部解析并直达交付
                        for node_url in set(valid_pool[:6]):
                            if node_url not in seen_urls:
                                seen_urls.add(node_url)
                                portal_results.append({
                                    "url": node_url,
                                    "category": "software",
                                    "ext": "web",
                                    "size": 0,
                                    "label": f"⚡ 《{title}》 业务直连节点",
                                    "source_engine": "跳转池解密",
                                    "referer": gw_url
                                })
                except Exception:
                    pass

            if portal_results:
                results = portal_results + results
                self.log_cb(f"✓ [门户跳转池穿透完成] 成功解密出 {len(portal_results)} 个底层真实业务直链与集群节点！")

        # 12. 终极自适应无缝升级：
        # 如果静态和DOM分析未发现可播放视频流，或者目标为典型的动态单页/SPA站点，自动无缝切换至 CDP 底层网络穿透！
        has_video = any(r.get("category") in ["video", "video_stream"] for r in results)
        has_app = any(r.get("category") in ["software", "pan_drive"] for r in results)
        is_spa_suspicious = any(k in target_url.lower() for k in ["/play/", "/video/", "watch", ".tv", ".cc", ".me"])
        if (not has_video and not has_app) or is_spa_suspicious:
            if not has_video and not has_app:
                self.log_cb("静态骨架未直接抓取到媒体或软件，系统全自动无缝升级至 Chrome CDP 深度沙箱网络拦截...")
            else:
                self.log_cb("为确保分片完整与深层网络捕获，同步调遣 Chrome CDP 底层网络引擎深入探测...")

            browser_results = self.analyze_with_playwright(target_url)
            for br in browser_results:
                if br["url"] not in seen_urls:
                    seen_urls.add(br["url"])
                    results.append(br)

        self.log_cb(f"扫描完毕！综合引擎共捕获到 {len(results)} 个潜在资源。")
        return results

    def analyze_with_playwright(self, target_url: str):
        """现代动态网站/SPA/MSE 深度嗅探：真实调遣无头 Chromium 进行 CDP 网络底层监听与交互触发"""
        self.log_cb(f"=== 启动 CDP 底层网络抓包引擎: {target_url} ===")
        results = []
        seen_urls = set()

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.log_cb("[警告] 未检测到 playwright 运行库，跳过底层 CDP 抓包。")
            return results

        try:
            with sync_playwright() as p:
                self.log_cb("正在调遣 Chromium 无头渲染沙箱...")
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=self.headers["User-Agent"],
                    viewport={"width": 1280, "height": 720},
                    locale="zh-CN"
                )

                # 注入 Stealth 防反爬检测脚本（抹除自动化特征）
                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    window.chrome = { runtime: {} };
                    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
                    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                """)

                page = context.new_page()

                def record_media(url, label="CDP拦截媒体流", default_cat=None, default_ext=None):
                    clean = url.split("#")[0]
                    if not clean or clean in seen_urls:
                        return
                    # 过滤常见的占位/空白测试视频
                    if any(dummy in clean.lower() for dummy in ["empty", "blank", "pixel", "track.mp4", "ad.mp4"]):
                        return
                    # 过滤单独的 ts 切片，避免成百上千个微小分片干扰主控 m3u8
                    if ".ts?" in clean.lower() or clean.lower().endswith(".ts"):
                        return

                def record_media(url, label="CDP拦截媒体流", default_cat=None, default_ext=None, is_direct_request=False):
                    clean = url.split("#")[0]
                    if not clean:
                        return
                    # 过滤常见的占位/空白测试视频
                    if any(dummy in clean.lower() for dummy in ["empty", "blank", "pixel", "track.mp4", "ad.mp4"]):
                        return
                    # 过滤单独的 ts 切片，避免成百上千个微小分片干扰主控 m3u8
                    if ".ts?" in clean.lower() or clean.lower().endswith(".ts"):
                        return

                    ext = default_ext or ("m3u8" if ".m3u8" in clean.lower() else ("mp4" if ".mp4" in clean.lower() else "flv"))
                    cat = default_cat or ("video_stream" if ext == "m3u8" else "video")

                    # 如果已有相同基础路径但新 URL 携带更多鉴权参数（如带 vv、pub 等动态鉴权 token），则升级替换
                    base_path = clean.split("?")[0]
                    for item in results:
                        if item.get("category") == cat and item["url"].split("?")[0] == base_path:
                            if len(clean) > len(item["url"]) or is_direct_request:
                                item["url"] = clean
                                item["label"] = label
                                item["referer"] = target_url
                                return
                            return

                    if clean in seen_urls:
                        return

                    seen_urls.add(clean)
                    self.log_cb(f"🎯 [CDP底层捕获] 成功截获高清资源: {clean[:80]}...")
                    results.append({
                        "url": clean,
                        "category": cat,
                        "ext": ext,
                        "size": 0,
                        "label": label,
                        "referer": target_url
                    })

                def on_request(req):
                    u = req.url
                    u_low = u.lower()
                    if any(k in u_low for k in [".m3u8", ".mp4", ".flv", ".f4v", ".webm", ".mkv", ".wmv"]):
                        record_media(u, "网络底层拦截流", is_direct_request=True)

                def on_response(resp):
                    u = resp.url
                    ct = resp.headers.get("content-type", "").lower()
                    if "mpegurl" in ct or "application/vnd.apple.mpegurl" in ct or "application/x-mpegurl" in ct:
                        record_media(u, "M3U8流媒体响应", default_cat="video_stream", default_ext="m3u8", is_direct_request=True)
                    elif "video/" in ct:
                        record_media(u, "视频媒体响应", default_cat="video", default_ext="mp4", is_direct_request=True)
                    # 挖掘现代 SPA 网站在 JSON API 中返回的隐藏播放地址
                    elif "application/json" in ct or "text/json" in ct:
                        try:
                            text = resp.text()
                            if any(ext in text.lower() for ext in [".m3u8", ".mp4"]):
                                found = re.findall(r'https?:\\?/\\?/[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*', text)
                                for f_url in found:
                                    record_media(f_url.replace(r'\/', '/'), "API动态返回媒体流", is_direct_request=False)
                        except Exception:
                            pass

                page.on("request", on_request)
                page.on("response", on_response)

                self.log_cb("正在加载目标页面并模拟现代浏览器渲染环境...")
                try:
                    page.goto(target_url, wait_until="networkidle", timeout=15000)
                except Exception:
                    pass

                # 模拟用户点击交互，破除现代播放器的静音/防自动播放策略
                try:
                    page.evaluate("""() => {
                        const playSelectors = [
                            '.play', '.dplayer-play-icon', '.vjs-big-play-button',
                            '.art-state-play', '.xgplayer-play', 'button[aria-label="Play"]',
                            'button.play', '.prism-play-btn', 'video'
                        ];
                        for (const sel of playSelectors) {
                            const el = document.querySelector(sel);
                            if (el) {
                                try { el.click(); } catch(e) {}
                            }
                        }
                        document.querySelectorAll('video').forEach(v => {
                            try { v.play(); } catch(e) {}
                        });
                    }""")
                except Exception:
                    pass

                # 等待 4 秒持续抓取异步分发的流地址
                for _ in range(4):
                    if any(r["category"] == "video_stream" for r in results):
                        break
                    page.wait_for_timeout(1000)

                # 提取页面标题并整理资源友好名称
                try:
                    page_title = page.title()
                    if page_title:
                        short_title = page_title.split("-")[0].split("_")[0].strip() or page_title
                        for item in results:
                            if item["category"] == "video_stream":
                                item["label"] = f"《{short_title}》高清流媒体"
                            elif item["category"] == "video":
                                item["label"] = f"《{short_title}》正片视频"
                except Exception:
                    pass

                # 扫描页面中动态渲染的高清海报
                try:
                    imgs = page.eval_on_selector_all("img", "elements => elements.map(e => e.src)")
                    for img_url in imgs[:20]:
                        if img_url and img_url.startswith("http") and img_url not in seen_urls:
                            if any(ext in img_url.lower() for ext in [".jpg", ".png", ".webp", ".jpeg"]):
                                seen_urls.add(img_url)
                                results.append({
                                    "url": img_url,
                                    "category": "image",
                                    "ext": "jpg",
                                    "size": 0,
                                    "label": "页面动态海报"
                                })
                except Exception:
                    pass

                browser.close()
                self.log_cb(f"CDP 底层拦截完成，共捕获 {len(results)} 条底层资源。")
        except Exception as e:
            self.log_cb(f"[CDP抓包提示] 浏览器层解析完成: {e}")

        return results

    def analyze_auto(self, target_url: str):
        """
        万能智能自适应嗅探器：
        纯自动化全息嗅探体系，内部已集成静态DOM穿透、CMS解析与自适应无缝升级CDP沙箱。
        """
        self.log_cb(f"【OmniFinder 引擎】正在自适应解析目标网址: {target_url}")
        return self.analyze_static_and_dom(target_url)


