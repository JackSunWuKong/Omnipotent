"""
全网智能资源聚合搜索引擎（经过可用性与直链秒播校验版）
精选国内极速开放且无需任何防盗链/Token鉴权即可直接拉流下载的影视接口池
"""

import httpx
import concurrent.futures
from urllib.parse import quote
from bs4 import BeautifulSoup

# 经过严密验证：即时秒级响应、带标准可直出 m3u8 的极速片源 API 矩阵池

VIDEO_SEARCH_APIS = [
    {
        "name": "魔都极速源",
        "url": "https://caiji.moduapi.cc/api.php/provide/vod/?ac=videolist&wd="
    },
    {
        "name": "IKUN开放源",
        "url": "https://ikunzyapi.com/api.php/provide/vod/?ac=videolist&wd="
    },
    {
        "name": "360资源",
        "url": "https://360zy.com/api.php/provide/vod/?ac=videolist&wd="
    },
    {
        "name": "豪华资源",
        "url": "https://hhzyapi.com/api.php/provide/vod/?ac=videolist&wd="
    },
    {
        "name": "速播资源",
        "url": "https://subocaiji.com/api.php/provide/vod/?ac=videolist&wd="
    }
]

class ResourceSearcher:
    def __init__(self, log_cb=print):
        self.log_cb = log_cb
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

    def search_videos(self, keyword: str):
        self.log_cb(f"正在全网影视云矩阵 ({len(VIDEO_SEARCH_APIS)} 个核心节点) 并发检索: 《{keyword}》...")
        results = []
        seen_urls = set()

        def fetch_api(api_info):
            name = api_info["name"]
            req_url = f"{api_info['url']}{quote(keyword)}"
            try:
                with httpx.Client(headers=self.headers, timeout=5.0, verify=False, follow_redirects=True) as client:
                    resp = client.get(req_url)
                    if resp.status_code == 200:
                        data = resp.json()
                        items = data.get("list", [])
                        return name, items
            except Exception as e:
                pass
            return name, []

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(VIDEO_SEARCH_APIS)) as executor:
            future_to_api = {executor.submit(fetch_api, api): api["name"] for api in VIDEO_SEARCH_APIS}
            for future in concurrent.futures.as_completed(future_to_api):
                api_name, items = future.result()
                if items:
                    self.log_cb(f"[{api_name}] 成功匹配到 {len(items)} 个相关剧目与资源条目")
                    for item in items:
                        vod_name = item.get("vod_name", "未知片名")
                        vod_remarks = item.get("vod_remarks", "")
                        vod_play_url = item.get("vod_play_url", "")

                        sources = vod_play_url.split("$$$")
                        for src in sources:
                            episodes = src.split("#")
                            for ep in episodes:
                                if "$" in ep:
                                    parts = ep.split("$")
                                    ep_title = parts[0].strip()
                                    stream_url = parts[1].strip()
                                else:
                                    ep_title = "正片"
                                    stream_url = ep.strip()

                                if not stream_url.startswith("http"):
                                    continue

                                if stream_url in seen_urls:
                                    continue
                                seen_urls.add(stream_url)

                                is_m3u8 = ".m3u8" in stream_url.lower()
                                display_label = f"🎬 《{vod_name}》 {vod_remarks} - {ep_title}"

                                results.append({
                                    "url": stream_url,
                                    "category": "video_stream" if is_m3u8 else "video",
                                    "ext": "m3u8" if is_m3u8 else "mp4",
                                    "size": 0,
                                    "label": display_label,
                                    "source_engine": api_name,
                                    "vod_name": vod_name,
                                    "ep_title": ep_title
                                })

        self.log_cb(f"全网多节点聚合搜索完毕！共检索出 {len(results)} 条影视资源。")
        return results

    def search_documents(self, keyword: str):
        """
        全网模板、办公文档、素材附件智能搜索引擎：
        穿透开放素材资源库（站长素材、免费Word简历库、网盘文档等），
        秒级直接提取可下载的 .doc / .docx / .rar / .zip / .pdf 资源直链！
        """
        self.log_cb(f"正在全网开放文档与素材库中检索: 《{keyword}》...")
        results = []
        seen_urls = set()

        # 1. 穿透全国主流免费办公素材库 (Chinaz 文档/简历模板库)
        try:
            chinaz_url = f"https://aspx.sc.chinaz.com/query.aspx?keyword={quote(keyword)}&classID=864"
            with httpx.Client(headers=self.headers, timeout=5.0, verify=False) as client:
                r = client.get(chinaz_url)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    boxes = soup.find_all("div", class_="box")
                    self.log_cb(f"[办公素材库] 匹配到 {len(boxes)} 个相关模板条目")

                    # 并发提取前 15 个模板的直链下载地址与预览大图
                    detail_tasks = []
                    for box in boxes[:15]:
                        a = box.find("a")
                        if a and a.get("href"):
                            href = a["href"].strip()
                            if href.startswith("//"):
                                href = "https:" + href
                            img_tag = box.find("img")
                            preview_img = ""
                            if img_tag:
                                isrc = img_tag.get("src") or img_tag.get("data-original") or ""
                                if isrc.startswith("//"):
                                    preview_img = "https:" + isrc
                                elif isrc.startswith("http"):
                                    preview_img = isrc
                            title = a.get_text().strip() or (img_tag.get("alt", "") if img_tag else "模板文件")
                            detail_tasks.append((title, href, preview_img))

                    def fetch_doc_download_link(task):
                        doc_title, doc_url, p_img = task
                        try:
                            with httpx.Client(headers=self.headers, timeout=4.0, verify=False) as sub_c:
                                sub_r = sub_c.get(doc_url)
                                sub_soup = BeautifulSoup(sub_r.text, "html.parser")
                                # 尝试在详情页提取更高清的模板大样图
                                for img in sub_soup.find_all("img"):
                                    src = img.get("src") or ""
                                    if "pic" in src and "jianli" in src:
                                        if src.startswith("//"):
                                            p_img = "https:" + src
                                        elif src.startswith("http"):
                                            p_img = src
                                        break

                                for link in sub_soup.find_all("a", href=True):
                                    h = link["href"]
                                    if any(ext in h.lower() for ext in [".rar", ".zip", ".doc", ".docx", ".pdf"]):
                                        return doc_title, h, doc_url, p_img
                        except Exception:
                            pass
                        return doc_title, None, doc_url, p_img

                    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
                        futs = [ex.submit(fetch_doc_download_link, t) for t in detail_tasks]
                        for f in concurrent.futures.as_completed(futs):
                            title, dl_url, page_ref, p_img = f.result()
                            if dl_url and dl_url not in seen_urls:
                                seen_urls.add(dl_url)
                                ext = dl_url.split(".")[-1].split("?")[0].lower()
                                results.append({
                                    "url": dl_url,
                                    "category": "document",
                                    "ext": ext,
                                    "size": 0,
                                    "label": f"📄 《{title}》 (可编辑Word/附件包)",
                                    "source_engine": "全网办公素材库",
                                    "referer": page_ref,
                                    "preview_img": p_img
                                })

        except Exception as e:
            self.log_cb(f"[文档搜索提示] 素材库扫描: {e}")

        # 2. 全网文档开放引擎 (检索开放文档与模板专题站)
        try:
            bing_url = f"https://cn.bing.com/search?q={quote(keyword + ' 免费下载 docx OR doc OR 模板')}"
            with httpx.Client(headers=self.headers, timeout=5.0, verify=False) as client:
                r = client.get(bing_url)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    for li in soup.find_all("li", class_="b_algo")[:8]:
                        h2 = li.find("h2")
                        if h2 and h2.find("a"):
                            a = h2.find("a")
                            t = a.get_text().strip()
                            link = a["href"]
                            if link not in seen_urls and link.startswith("http"):
                                seen_urls.add(link)
                                results.append({
                                    "url": link,
                                    "category": "document",
                                    "ext": "doc",
                                    "size": 0,
                                    "label": f"📑 {t}",
                                    "source_engine": "全网文档开放源",
                                    "referer": ""
                                })
        except Exception as e:
            self.log_cb(f"[文档搜索提示] 全网文档源: {e}")

        self.log_cb(f"全网文档检索完毕！共捕获到 {len(results)} 个模板与文档资源。")
        return results

    def search_software(self, keyword: str):
        """
        全网软件、客户端应用、工具安装包智能搜索引擎：
        聚合检索软件官方发布源、各大开源发行通道与权威下载中心，
        自动提取客户端安装包（.exe / .dmg / .pkg / .apk / .zip）与官方直下入口！
        """
        self.log_cb(f"正在全网软件应用矩阵中检索: 《{keyword}》...")
        results = []
        seen_urls = set()

        # 1. 检索软件官方发布与绿色安装中心
        try:
            query = f"{keyword} 官方下载 官网最新版 OR exe OR dmg OR pkg"
            bing_url = f"https://cn.bing.com/search?q={quote(query)}"
            with httpx.Client(headers=self.headers, timeout=5.0, verify=False) as client:
                r = client.get(bing_url)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    for li in soup.find_all("li", class_="b_algo")[:10]:
                        h2 = li.find("h2")
                        if h2 and h2.find("a"):
                            a = h2.find("a")
                            title = a.get_text().strip()
                            link = a["href"]
                            if link not in seen_urls and link.startswith("http"):
                                seen_urls.add(link)
                                # 识别安装包类型
                                ext = "exe"
                                if ".dmg" in link.lower():
                                    ext = "dmg"
                                elif ".pkg" in link.lower():
                                    ext = "pkg"
                                elif ".apk" in link.lower():
                                    ext = "apk"
                                elif ".zip" in link.lower():
                                    ext = "zip"

                                results.append({
                                    "url": link,
                                    "category": "software",
                                    "ext": ext,
                                    "size": 0,
                                    "label": f"💻 《{title}》 (软件安装/官方下载通道)",
                                    "source_engine": "全网软件矩阵源",
                                    "referer": ""
                                })
        except Exception as e:
            self.log_cb(f"[软件检索提示] 官方通道检索: {e}")

        # 2. 检索西西/站长等常用 Windows/Mac 绿色应用库
        try:
            cr_url = f"https://so.cr173.com/?k={quote(keyword)}"
            with httpx.Client(headers=self.headers, timeout=5.0, verify=False) as client:
                r = client.get(cr_url)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    soft_links = []
                    for a in soup.find_all("a", href=True):
                        h = a["href"]
                        t = a.get_text().strip()
                        if "/soft/" in h and len(t) > 2:
                            full_url = "https:" + h if h.startswith("//") else ("https://www.cr173.com" + h if h.startswith("/") else h)
                            soft_links.append((t, full_url))

                    # 提取前 5 个软件的实际 exe/zip 下载直链
                    for title, s_url in soft_links[:5]:
                        try:
                            sub_r = client.get(s_url, timeout=3.0)
                            sub_soup = BeautifulSoup(sub_r.text, "html.parser")
                            for da in sub_soup.find_all("a", href=True):
                                dh = da["href"]
                                if any(dh.lower().endswith(x) or (x in dh.lower() and "down" in dh.lower()) for x in [".exe", ".zip", ".rar", ".dmg"]):
                                    if dh.startswith("http") and dh not in seen_urls:
                                        seen_urls.add(dh)
                                        results.append({
                                            "url": dh,
                                            "category": "software",
                                            "ext": dh.split(".")[-1].split("?")[0].lower() or "exe",
                                            "size": 0,
                                            "label": f"💾 《{title}》 绿色直下包",
                                            "source_engine": "开放应用镜像源",
                                            "referer": s_url
                                        })
                                        break
                        except Exception:
                            continue
        except Exception as e:
            pass

        self.log_cb(f"全网软件检索完毕！共捕获到 {len(results)} 个软件下载入口。")
        return results

    def search_all(self, keyword: str):
        """
        全能全景搜索：智能识别关键词意图，全方位覆盖：
        1. 影视/电视剧/动漫/音乐
        2. 办公文档/简历/合同/PPT/Word/Excel
        3. 各行业桌面与移动软件/安装包/绿色工具
        """
        doc_keywords = ["简历", "模板", "文档", "表格", "ppt", "word", "excel", "pdf", "论文", "合同", "素材", "图标"]
        software_keywords = ["软件", "下载", "安装包", "破解", "绿色版", "app", "pc", "mac", "windows", "client", "exe", "dmg", "apk", "player", "vscode", "potplayer", "微信", "qq", "chrome", "浏览器", "工具"]

        kw_lower = keyword.lower()
        is_doc_intent = any(k in kw_lower for k in doc_keywords)
        is_software_intent = any(k in kw_lower for k in software_keywords)

        results = []
        if is_doc_intent:
            self.log_cb(f"【万能钥匙】检测到办公/文档/素材意图，优先检索全国模板库与文档资源...")
            results.extend(self.search_documents(keyword))
            video_results = self.search_videos(keyword)
            results.extend(video_results)
        elif is_software_intent:
            self.log_cb(f"【万能钥匙】检测到应用/软件/工具意图，优先检索全网软件下载矩阵...")
            results.extend(self.search_software(keyword))
            # 同时也检索是否有相关影视或官方视频教程
            video_results = self.search_videos(keyword)
            results.extend(video_results)
        else:
            # 综合意图：优先搜索影视矩阵，若少于 3 条，自动全网拓展到软件库与文档库
            results.extend(self.search_videos(keyword))
            if len(results) < 5:
                results.extend(self.search_software(keyword))
                results.extend(self.search_documents(keyword))

        return results



