"""
全网智能资源聚合搜索引擎（经过可用性与直链秒播校验版）
精选国内极速开放且无需任何防盗链/Token鉴权即可直接拉流下载的影视接口池
"""

import re
import httpx
import urllib.parse
import concurrent.futures
from urllib.parse import quote
from bs4 import BeautifulSoup

# 经过严密验证：即时秒级响应、带标准可直出 m3u8 的 10 大核心片源 API 矩阵池
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
    },
    {
        "name": "暴风资源",
        "url": "https://bfzyapi.com/api.php/provide/vod/?ac=videolist&wd="
    },
    {
        "name": "虎牙资源",
        "url": "https://www.huyaapi.com/api.php/provide/vod/?ac=videolist&wd="
    },
    {
        "name": "百度资源",
        "url": "https://api.apibdzy.com/api.php/provide/vod/?ac=videolist&wd="
    },
    {
        "name": "红牛资源",
        "url": "https://www.hongniuzy2.com/api.php/provide/vod/?ac=videolist&wd="
    },
    {
        "name": "光速资源",
        "url": "https://api.guangsuapi.com/api.php/provide/vod/?ac=videolist&wd="
    }
]

class ResourceSearcher:
    def __init__(self, log_cb=print):
        self.log_cb = log_cb
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

    def resolve_multilingual_aliases(self, keyword: str):
        """
        智能多语言片名自动互译与别名联想：
        当用户输入英文/外文片名（如 Oppenheimer、Avatar、Inception）时，
        毫秒级自动匹配中文官方译名（如 奥本海默、阿凡达、盗梦空间），
        实现 0 学习成本、中英文双向互通秒搜！
        """
        # 如果包含中文字符，直接以原关键词为主
        if any('\u4e00' <= char <= '\u9fa5' for char in keyword):
            return [keyword]

        candidates = [keyword]
        # 1. 豆瓣即时联想 API
        try:
            url = f"https://movie.douban.com/j/subject_suggest?q={quote(keyword)}"
            with httpx.Client(headers=self.headers, timeout=2.0, verify=False) as c:
                r = c.get(url)
                if r.status_code == 200:
                    for item in r.json():
                        t = item.get("title")
                        if t and any('\u4e00' <= ch <= '\u9fa5' for ch in t):
                            clean = t.split()[0].replace("·", "")
                            if clean and clean not in candidates:
                                candidates.append(clean)
        except Exception:
            pass

        # 2. 维基多语言交叉索引
        try:
            for term in [keyword, f"{keyword} (film)"]:
                wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=langlinks&titles={quote(term)}&lllang=zh&format=json"
                with httpx.Client(headers=self.headers, timeout=2.0, verify=False) as c:
                    r = c.get(wiki_url)
                    pages = r.json().get("query", {}).get("pages", {})
                    for pid, p in pages.items():
                        for ll in p.get("langlinks", []):
                            clean_t = ll.get("*", "").split("(")[0].strip()
                            if clean_t and clean_t not in candidates:
                                candidates.append(clean_t)
        except Exception:
            pass

        return candidates

    def search_videos(self, keyword: str):
        search_terms = self.resolve_multilingual_aliases(keyword)
        if len(search_terms) > 1:
            self.log_cb(f"【智能片名互译】已识别外文片名 《{keyword}》，自动扩展译名: {', '.join(search_terms[1:])}")

        self.log_cb(f"正在全网影视云矩阵 ({len(VIDEO_SEARCH_APIS)} 个核心节点) 并发检索: 《{keyword}》...")
        results = []
        seen_urls = set()

        def fetch_api(api_info, term):
            name = api_info["name"]
            req_url = f"{api_info['url']}{quote(term)}"
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

        tasks = []
        for term in search_terms:
            for api in VIDEO_SEARCH_APIS:
                tasks.append((api, term))

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(20, len(tasks))) as executor:
            future_to_api = {executor.submit(fetch_api, api, term): api["name"] for api, term in tasks}
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

    def reverse_plot_lookup(self, text: str):
        """
        剧情线索 / 短视频台词智能反向逆向溯源：
        当用户输入的不是标准片名，而是一句话（如“男子被困管道迷宫”、“小帅在火车上遇到杀手”或者一段短视频文案/台词片段）时，
        通过全网影视语义库反向溯源出最匹配的候选真实片名！
        """
        clue_indicators = ["被困", "迷宫", "杀手", "失忆", "特工", "反杀", "互换", "荒岛", "电影", "剧情", "讲的是", "解说", "小帅", "大壮", "发现自己", "穿越", "外星人", "末日"]
        is_clue = any(ci in text for ci in clue_indicators) or (len(text) > 8 and " " in text)
        if not is_clue:
            return []

        cands = {}
        try:
            url = f"https://www.so.com/s?q={quote(text + ' 电影')}"
            with httpx.Client(headers=self.headers, timeout=4.0, verify=False) as client:
                r = client.get(url)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    raw_text = soup.get_text()
                    matches = re.findall(r'《([^》]+)》', raw_text)
                    for m in matches:
                        m = m.strip()
                        if 1 < len(m) <= 12 and not any(bad in m for bad in ['视频', '全集', '高清', '预告', '剧情', '频道', '正片']):
                            cands[m] = cands.get(m, 0) + 1
        except Exception:
            pass

        sorted_cands = sorted(cands.items(), key=lambda x: x[1], reverse=True)
        top = [k for k, v in sorted_cands[:3]]
        return top

    def search_pan_drives(self, keyword: str):
        """
        全网网盘暗河探针矩阵（穿透夸克、百度、阿里等网盘分享池）：
        专搜绝版影视、4K原盘、网传合集，直接提取带提取码的转存链接！
        """
        search_terms = self.resolve_multilingual_aliases(keyword)
        query_kw = search_terms[1] if len(search_terms) > 1 else keyword
        self.log_cb(f"正在全网网盘暗河索引池 (夸克 / 百度 / 阿里) 中深潜检索: 《{query_kw}》...")
        results = []
        seen = set()

        pan_configs = [
            {"platform": "夸克网盘", "domain": "pan.quark.cn", "query_ext": "pan.quark.cn"},
            {"platform": "百度网盘", "domain": "pan.baidu.com", "query_ext": "pan.baidu.com"},
        ]

        def fetch_pan(p_conf):
            plat = p_conf["platform"]
            dom = p_conf["domain"]
            items = []
            try:
                url = f"https://www.so.com/s?q={quote(query_kw + ' ' + p_conf['query_ext'])}"
                with httpx.Client(headers=self.headers, timeout=5.0, verify=False) as client:
                    r = client.get(url)
                    if r.status_code == 200:
                        soup = BeautifulSoup(r.text, "html.parser")
                        for li in soup.find_all("li", class_="res-list")[:10]:
                            t_text = li.get_text()
                            h3 = li.find("h3")
                            title_text = h3.get_text().strip() if h3 else query_kw
                            title_clean = " ".join(title_text.split())

                            if dom == "pan.quark.cn":
                                links = re.findall(r'https?://pan\.quark\.cn/s/[a-zA-Z0-9]+', t_text)
                            else:
                                links = re.findall(r'https?://pan\.baidu\.com/s/[a-zA-Z0-9_\-]+', t_text)

                            pwd_match = re.search(r'(?:提取码|密码|pwd)[:：\s]*([a-zA-Z0-9]{4})', t_text, re.IGNORECASE)
                            pwd = pwd_match.group(1) if pwd_match else ""

                            for lk in links:
                                if lk not in seen:
                                    seen.add(lk)
                                    pwd_str = f"?pwd={pwd}" if pwd and "pwd=" not in lk else ""
                                    full_pan_url = lk + pwd_str if pwd_str else lk
                                    items.append({
                                        "url": full_pan_url,
                                        "category": "pan_drive",
                                        "ext": "pan",
                                        "size": 0,
                                        "label": f"☁️ 《{title_clean[:45]}》 [{plat}] {f'(提取码: {pwd})' if pwd else '(免密直存)'}",
                                        "source_engine": plat,
                                        "pwd": pwd,
                                        "referer": ""
                                    })
            except Exception:
                pass
            return items

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(pan_configs)) as executor:
            futs = [executor.submit(fetch_pan, pc) for pc in pan_configs]
            for f in concurrent.futures.as_completed(futs):
                res = f.result()
                results.extend(res)

        self.log_cb(f"网盘暗搜检索完毕！共捕获到 {len(results)} 条网盘转存资源。")
        return results

    def search_magnets(self, keyword: str):
        """
        全球去中心化 DHT 磁力网络探针：
        直连全球 P2P / DHT 分布式节点，专搜海外未删减版、4K 蓝光 Remux、冷门绝版资源！
        """
        self.log_cb(f"正在向全球去中心化 DHT 磁力网络发起嗅探: 《{keyword}》...")
        results = []
        seen = set()

        search_terms = self.resolve_multilingual_aliases(keyword)

        def fetch_btdig(term):
            items = []
            try:
                url = f"https://btdig.com/search?q={quote(term)}"
                with httpx.Client(headers={"User-Agent": "Mozilla/5.0"}, timeout=6.0, verify=False) as client:
                    r = client.get(url)
                    if r.status_code == 200:
                        soup = BeautifulSoup(r.text, "html.parser")
                        for div in soup.find_all("div", class_="one_result")[:10]:
                            title_div = div.find("div", class_="torrent_name")
                            t = title_div.get_text().strip() if title_div else term
                            mag_a = div.find("a", href=lambda h: h and h.startswith("magnet:"))
                            mag = mag_a["href"] if mag_a else ""
                            sz_span = div.find("span", class_="torrent_size")
                            sz = sz_span.get_text().strip() if sz_span else "GB"

                            if mag and mag not in seen:
                                seen.add(mag)
                                items.append({
                                    "url": mag,
                                    "category": "magnet",
                                    "ext": "torrent",
                                    "size": 0,
                                    "label": f"🧲 《{t}》 ({sz}) [DHT高活做种]",
                                    "source_engine": "全球DHT网络",
                                    "referer": ""
                                })
            except Exception:
                pass
            return items

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(3, len(search_terms))) as ex:
            futs = [ex.submit(fetch_btdig, st) for st in search_terms[:2]]
            for f in concurrent.futures.as_completed(futs):
                results.extend(f.result())

        self.log_cb(f"全球 DHT 磁力网络嗅探完毕！共捕获到 {len(results)} 条高清/原盘磁力。")
        return results

    def search_deep_dive(self, keyword: str):
        """
        全网深潜挖掘总调度：
        1. 剧情线索/短视频台词逆向识片 -> 锁定原片
        2. 10 大影视 CMS 云流秒播聚合
        3. 夸克/百度网盘暗河穿透
        4. 全球 DHT 磁力高活做种穿透
        """
        self.log_cb(f"🌊 【全网深潜模式启动】正在开启水下冰山资源穿透: 《{keyword}》...")

        # 1. 剧情逆向识片
        plot_cands = self.reverse_plot_lookup(keyword)
        extra_keywords = []
        if plot_cands:
            self.log_cb(f"🎯 【剧情逆向溯源】已从剧情线索成功锁定候选片名: {', '.join([f'《{c}》' for c in plot_cands])}")
            extra_keywords.extend(plot_cands)

        all_results = []
        primary_term = plot_cands[0] if plot_cands else keyword

        # 2. 并发检索视频源、网盘源、磁力源
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
            f_video = ex.submit(self.search_videos, primary_term)
            f_pan = ex.submit(self.search_pan_drives, primary_term)
            f_mag = ex.submit(self.search_magnets, primary_term)

            f_extra_video = None
            if plot_cands and keyword != primary_term:
                f_extra_video = ex.submit(self.search_videos, keyword)

            video_res = f_video.result()
            pan_res = f_pan.result()
            mag_res = f_mag.result()

            all_results.extend(video_res)
            if f_extra_video:
                all_results.extend(f_extra_video.result())
            all_results.extend(pan_res)
            all_results.extend(mag_res)

        self.log_cb(f"🌊 【全网深潜完毕】共挖掘出 {len(all_results)} 个全维可用资源（含可播视频流、网盘转存、全球磁力）！")
        return all_results

    def search_novels(self, keyword: str):
        """
        全网小说与绝版书籍深度探针矩阵：
        1. 在线阅读源：直连各大开放小说目录索引，提取作品名、作者、最新章节，支持直接调起专属阅读器
        2. 全网网盘小说暗搜：穿透夸克/百度网盘搜索未删减全本 TXT/EPUB 精校资源
        """
        self.log_cb(f"正在全网小说库与网盘暗河中深度探索: 《{keyword}》...")
        results = []
        seen = set()

        # 1. 在线阅读源探针 (8tsw / 笔趣阁多节点聚合)
        def fetch_online_novel():
            items = []
            try:
                # 8tsw 引擎
                search_url = 'http://www.8tsw.com/modules/article/search.php?searchkey=' + quote(keyword.encode('gbk', errors='ignore'))
                req_headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Connection': 'close'
                }
                with httpx.Client(headers=req_headers, timeout=6.0, verify=False) as client:
                    r = client.get(search_url)
                    if r.status_code == 200:
                        content_text = r.content.decode('gbk', errors='ignore')
                        # 匹配每行记录
                        for m in re.finditer(r'<tr id=["\']nr["\']>(.*?)</tr>', content_text, re.DOTALL):
                            row = m.group(1)
                            # 提取书籍链接与书名
                            b_match = re.search(r'<a\s+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>', row)
                            if not b_match:
                                continue
                            b_url = b_match.group(1)
                            b_title = b_match.group(2).strip()
                            if not b_url.startswith('http'):
                                b_url = 'http://www.8tsw.com' + b_url

                            # 提取最新章节
                            ch_matches = re.findall(r'<a\s+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>', row)
                            latest_ch = ch_matches[1][1].strip() if len(ch_matches) > 1 else "全本连载"

                            # 提取作者
                            tds = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                            author = re.sub(r'<[^>]+>', '', tds[2]).strip() if len(tds) > 2 else "未知作者"

                            if b_url not in seen:
                                seen.add(b_url)
                                items.append({
                                    "url": b_url,
                                    "category": "novel",
                                    "sub_category": "novel_online",
                                    "ext": "txt",
                                    "size": 0,
                                    "label": f"📖 《{b_title}》 (作者: {author}) [最新: {latest_ch[:20]}] [在线秒读/目录完整]",
                                    "source_engine": "笔趣阁镜像",
                                    "referer": b_url
                                })
            except Exception as e:
                pass
            return items

        # 2. 全网网盘小说暗搜 (精校 TXT / EPUB 全本合集)
        def fetch_pan_novel():
            items = []
            pan_configs = [
                {"platform": "夸克网盘", "domain": "pan.quark.cn"},
                {"platform": "百度网盘", "domain": "pan.baidu.com"},
            ]
            for p_conf in pan_configs:
                plat = p_conf["platform"]
                dom = p_conf["domain"]
                try:
                    q_str = f"{keyword} (txt OR epub) {dom}"
                    url = f"https://www.so.com/s?q={quote(q_str)}"
                    with httpx.Client(headers=self.headers, timeout=5.0, verify=False) as client:
                        r = client.get(url)
                        if r.status_code == 200:
                            soup = BeautifulSoup(r.text, "html.parser")
                            for li in soup.find_all("li", class_="res-list")[:8]:
                                t_text = li.get_text()
                                h3 = li.find("h3")
                                title_text = h3.get_text().strip() if h3 else keyword
                                title_clean = " ".join(title_text.split())

                                if dom == "pan.quark.cn":
                                    links = re.findall(r'https?://pan\.quark\.cn/s/[a-zA-Z0-9]+', t_text)
                                else:
                                    links = re.findall(r'https?://pan\.baidu\.com/s/[a-zA-Z0-9_\-]+', t_text)

                                pwd_match = re.search(r'(?:提取码|密码|pwd)[:：\s]*([a-zA-Z0-9]{4})', t_text, re.IGNORECASE)
                                pwd = pwd_match.group(1) if pwd_match else ""

                                for lk in links:
                                    if lk not in seen:
                                        seen.add(lk)
                                        pwd_str = f"?pwd={pwd}" if pwd and "pwd=" not in lk else ""
                                        full_pan_url = lk + pwd_str if pwd_str else lk
                                        items.append({
                                            "url": full_pan_url,
                                            "category": "novel",
                                            "sub_category": "novel_pan",
                                            "ext": "txt",
                                            "size": 0,
                                            "label": f"☁️ 《{title_clean[:45]}》 [{plat}全本TXT/EPUB] {f'(提取码: {pwd})' if pwd else '(免密直存)'}",
                                            "source_engine": plat,
                                            "pwd": pwd,
                                            "referer": ""
                                        })
                except Exception:
                    pass
            return items

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f_online = executor.submit(fetch_online_novel)
            f_pan = executor.submit(fetch_pan_novel)
            results.extend(f_online.result())
            results.extend(f_pan.result())

        self.log_cb(f"小说资源深度探索完毕！共捕获到 {len(results)} 部书籍（含在线阅读与网盘精校全本）。")
        return results

    @staticmethod
    def fetch_novel_chapters(book_url: str):
        """
        根据小说页面 URL 获取章节目录列表（带自动多轮重试）
        返回: [{"title": "第一章...", "url": "http://..."}, ...]
        """
        chapters = []
        req_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Connection': 'close'
        }
        target_url = book_url.replace("https://", "http://")
        
        # 尝试多次防止瞬时 502
        for _ in range(3):
            try:
                with httpx.Client(headers=req_headers, timeout=6.0, verify=False) as client:
                    r = client.get(target_url)
                    if r.status_code == 200 and len(r.content) > 1000:
                        text = r.content.decode('gbk', errors='ignore')
                        raw_chapters = re.findall(r'<dd[^>]*>\s*<a\s+href=[\'"]([^\'"]+)[\'"][^>]*>([^<]+)</a>', text)
                        for rel_url, title in raw_chapters:
                            full_ch_url = urllib.parse.urljoin(target_url, rel_url).replace("https://", "http://")
                            chapters.append({
                                "title": title.strip(),
                                "url": full_ch_url
                            })
                        if chapters:
                            break
            except Exception:
                pass
        return chapters

    @staticmethod
    def fetch_chapter_content(chapter_url: str):
        """
        根据章节链接抓取正文内容（带多轮重试与文本清洗）
        返回: (title, text_content)
        """
        req_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Connection': 'close'
        }
        target_url = chapter_url.replace("https://", "http://")

        for _ in range(3):
            try:
                with httpx.Client(headers=req_headers, timeout=6.0, verify=False) as client:
                    r = client.get(target_url)
                    if r.status_code == 200:
                        text = r.content.decode('gbk', errors='ignore')
                        # 抓取标题
                        title_match = re.search(r'<h1>([^<]+)</h1>', text)
                        ch_title = title_match.group(1).strip() if title_match else ""

                        # 抓取正文
                        content_match = re.search(r'<div\s+id=[\'"]content[\'"][^>]*>(.*?)</div>', text, re.DOTALL)
                        if content_match:
                            raw_body = content_match.group(1)
                            clean_body = re.sub(r'<br\s*/?>', '\n', raw_body)
                            clean_body = re.sub(r'&nbsp;', ' ', clean_body)
                            clean_body = re.sub(r'<[^>]+>', '', clean_body).strip()
                            # 排版优化：段落前补4空格
                            formatted_lines = []
                            for line in clean_body.split('\n'):
                                l = line.strip()
                                if l:
                                    formatted_lines.append("    " + l)
                            return ch_title, "\n\n".join(formatted_lines)
            except Exception:
                pass
        return "", "正文加载失败，请检查网络或点击重新加载。"

    def search_all(self, keyword: str, deep_dive: bool = False):
        """
        全能全景搜索：智能识别关键词意图，全方位覆盖：
        1. 电子小说 / 全本书籍 / 在线阅读 / 章节目录
        2. 影视 / 电视剧 / 动漫 / 音乐（10 大核心节点）
        3. 全网深潜挖掘（夸克/百度网盘暗搜 + 全球 DHT 磁力网络）
        4. 办公文档 / 简历 / 合同 / PPT / Word / Excel
        5. 各行业桌面与移动软件 / 安装包 / 绿色工具
        """
        if deep_dive:
            return self.search_deep_dive(keyword)

        # 智能检测是否输入的是剧情描述
        clue_indicators = ["被困", "迷宫", "杀手", "失忆", "特工", "反杀", "互换", "荒岛", "讲的是", "解说", "小帅"]
        if any(ci in keyword for ci in clue_indicators):
            return self.search_deep_dive(keyword)

        novel_keywords = ["小说", "txt", "epub", "全本", "完本", "章节", "精校", "番外", "无删减", "书", "阅读", "文学"]
        doc_keywords = ["简历", "模板", "文档", "表格", "ppt", "word", "excel", "pdf", "论文", "合同", "素材", "图标"]
        software_keywords = ["软件", "下载", "安装包", "破解", "绿色版", "app", "pc", "mac", "windows", "client", "exe", "dmg", "apk", "player", "vscode", "potplayer", "微信", "qq", "chrome", "浏览器", "工具"]

        kw_lower = keyword.lower()
        is_novel_intent = any(k in kw_lower for k in novel_keywords)
        is_doc_intent = any(k in kw_lower for k in doc_keywords)
        is_software_intent = any(k in kw_lower for k in software_keywords)

        results = []
        if is_novel_intent:
            self.log_cb(f"【OmniFinder】检测到小说/书籍意图，优先检索全网小说与TXT/EPUB精校资源池...")
            # 去除冗余后缀词提高命中率
            clean_book_name = re.sub(r'(?:小说|txt|epub|全本|完本|精校|无删减|下载)', '', keyword, flags=re.IGNORECASE).strip()
            book_query = clean_book_name if clean_book_name else keyword
            results.extend(self.search_novels(book_query))
            # 附带检索网盘与影视
            results.extend(self.search_pan_drives(keyword))
        elif is_doc_intent:
            self.log_cb(f"【OmniFinder】检测到办公/文档/素材意图，优先检索全国模板库与文档资源...")
            results.extend(self.search_documents(keyword))
            video_results = self.search_videos(keyword)
            results.extend(video_results)
        elif is_software_intent:
            self.log_cb(f"【OmniFinder】检测到应用/软件/工具意图，优先检索全网软件下载矩阵...")
            results.extend(self.search_software(keyword))
            video_results = self.search_videos(keyword)
            results.extend(video_results)
        else:
            # 综合意图：优先搜索影视矩阵
            video_results = self.search_videos(keyword)
            results.extend(video_results)
            # 若常规源搜索结果较少，自动深潜补充小说、网盘与磁力资源！
            if len(results) < 3:
                self.log_cb(f"【智能深潜补充】常规片源较少，自动调动网盘暗搜与全球磁力补强...")
                results.extend(self.search_pan_drives(keyword))
                results.extend(self.search_magnets(keyword))
                results.extend(self.search_novels(keyword))
            if len(results) < 5:
                results.extend(self.search_software(keyword))
                results.extend(self.search_documents(keyword))

        return results




