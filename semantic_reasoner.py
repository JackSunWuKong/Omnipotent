"""
semantic_reasoner.py - 智能语义意图理解与剧情/台词逆向推导引擎
(Intelligent Semantic Intent Reasoner & Plot/Quote-to-Entity Engine)

核心目标：
解决用户“记不清片名/书名，只记得经典台词、剧情梗概、角色特征、错别字或模糊自然语言”时的检索难题。
通过自然语言解析、多层知识库与全网语义拓扑聚类，将自然语言逆向推导为确定性的真实标准作品名称。
"""

import re
import urllib.parse
import httpx
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup


class SemanticEntity:
    def __init__(self, title: str, category: str, confidence: float, aliases: List[str] = None, rationale: str = ""):
        self.title = title
        self.category = category  # "movie", "tv", "book", "anime", "software"
        self.confidence = confidence  # 0.0 - 1.0
        self.aliases = aliases or []
        self.rationale = rationale  # 推理依据

    def to_dict(self):
        return {
            "title": self.title,
            "category": self.category,
            "confidence": round(self.confidence, 2),
            "aliases": self.aliases,
            "rationale": self.rationale
        }


class SemanticReasoner:
    """
    语义意图推理机：
    1. 判断输入文本类型（短词精准型 vs 自然语言长句/台词/剧情描述型）
    2. 针对自然语言剧情描述，通过全网语义实体拓扑反向聚类
    3. 逆向提取真实标准作品名与别名矩阵
    """

    # 常见自然语言停用词与意图提示词
    INTENT_INDICATORS = [
        "那个", "讲的是", "主角", "台词", "剧情", "一部", "电影", "电视剧",
        "动漫", "小说", "讲", "怎么", "什么", "找一下", "想看", "里面有", "有个",
        "扮演", "叫什么", "是谁", "有关", "关于"
    ]

    # 排除的通用噪音词
    STOP_WORDS = {
        "水手", "哔哩哔哩", "bilibili", "腾讯视频", "爱奇艺", "优酷", "好看视频",
        "抖音", "快手", "百度百科", "高清", "在线观看", "视频", "电视剧", "电影",
        "小说", "动漫", "全集", "完整版", "新番吐槽", "官方", "解说"
    }

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

    def is_natural_language_query(self, query: str) -> bool:
        """
        判断用户输入是否为自然语言意图描述（而非单纯的标准片名）
        """
        q = query.strip()
        # 纯 URL 或标准视频文件后缀跳过
        if q.startswith("http") or any(q.lower().endswith(ext) for ext in [".m3u8", ".mp4", ".flv", ".torrent"]):
            return False

        if len(q) >= 6 and any(ind in q for ind in self.INTENT_INDICATORS):
            return True
        if len(q) >= 12:  # 较长语句大概率是剧情或台词
            return True
        if "?" in q or "？" in q or len(q.split()) >= 3:
            return True
        return False

    def deduce_entity_from_plot_or_quote(self, query: str) -> Optional[SemanticEntity]:
        """
        核心逆向推导方法：
        从模糊剧情、台词、人物关系中推导目标作品实体
        """
        clean_q = query.strip()
        if not clean_q:
            return None

        # 策略 1: 豆瓣电影/读书开放语义索引优先探测（若为标准名或高频别名秒出）
        entity = self._query_douban_suggest(clean_q)
        if entity and entity.confidence >= 0.8:
            return entity

        # 策略 2: 全网语义拓扑反向聚类（反向提取书名号与高频实体）
        entity = self._query_semantic_clustering(clean_q)
        if entity and entity.confidence >= 0.7:
            return entity

        return None

    def _query_douban_suggest(self, query: str) -> Optional[SemanticEntity]:
        """通过豆瓣电影快速语义关联接口尝试匹配"""
        try:
            encoded = urllib.parse.quote(query[:30])
            url = f"https://movie.douban.com/j/subject_suggest?q={encoded}"
            with httpx.Client(verify=False, timeout=3.0, headers=self.headers) as client:
                r = client.get(url)
                if r.status_code == 200:
                    items = r.json()
                    if isinstance(items, list) and len(items) > 0:
                        top = items[0]
                        title = top.get("title", "")
                        year = top.get("year", "")
                        sub_title = top.get("sub_title", "")
                        desc = top.get("desc", "")
                        if title:
                            rationale = f"豆瓣影视图谱匹配: {title} ({year}) {desc}"
                            return SemanticEntity(
                                title=title,
                                category="movie" if "movie" in top.get("type", "") else "media",
                                confidence=0.88,
                                aliases=[sub_title] if sub_title else [],
                                rationale=rationale
                            )
        except Exception:
            pass
        return None

    def _query_semantic_clustering(self, query: str) -> Optional[SemanticEntity]:
        """
        全网语义拓扑反向聚类：
        抓取搜索引擎返回的富文本卡片与标题，提取书名号【...】、《...》，并进行语义频次对齐与投票
        """
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://www.so.com/s?q={encoded}"
            with httpx.Client(verify=False, timeout=4.0, headers=self.headers) as client:
                r = client.get(url)
                if r.status_code != 200:
                    return None
                html = r.text

            # 1. 抽取书名号与方括号实体
            matches = re.findall(r'[《【]([^》】]{1,25})[》】]', html)
            vote_counter: Dict[str, int] = {}
            for m in matches:
                name = m.strip()
                if name in self.STOP_WORDS:
                    continue
                # 过滤明显是网页模板或杂音项
                if any(w in name for w in ["点击", "关注", "下载", "官方", "解说", "盘点", "书评", "简介", "阅读", "目录", "TXT", "epub"]):
                    continue
                vote_counter[name] = vote_counter.get(name, 0) + 1

            # 2. 如果书名号中有明显领跑的实体
            if vote_counter:
                sorted_votes = sorted(vote_counter.items(), key=lambda x: x[1], reverse=True)
                top_entity, freq = sorted_votes[0]
                if freq >= 2 or (freq >= 1 and len(sorted_votes) == 1):
                    return SemanticEntity(
                        title=top_entity,
                        category="media",
                        confidence=0.92 if freq >= 2 else 0.75,
                        rationale=f"AI 逆向语义聚类：根据台词/剧情线索锁定作品《{top_entity}》（全网权威度投票 {freq} 票）"
                    )

            # 3. 若无书名号，深度解析 h3 / h2 标题分词中的高频核心作品实体
            soup = BeautifulSoup(html, "html.parser")
            titles = [h.get_text().strip() for h in soup.find_all(['h3', 'h2']) if h.get_text().strip()]
            for t in titles:
                # 提取“新番：xxx”或“电影：xxx”或“《xxx》”
                m_sub = re.search(r'(?:新番|电影|电视剧|动漫|动画|剧集)[：:]\s*([^\s_,|#]+)', t)
                if m_sub:
                    cand = m_sub.group(1).strip()
                    if cand and cand not in self.STOP_WORDS:
                        return SemanticEntity(
                            title=cand,
                            category="media",
                            confidence=0.82,
                            rationale=f"AI 逆向语义推导：从上下文片名锚点锁定《{cand}》"
                        )

        except Exception:
            pass
        return None


# 全局单例
semantic_reasoner = SemanticReasoner()
