"""
全能国际化多语言管理总线 (Universal I18n Manager)
支持 简体中文、English、繁體中文、日本語、한국어
采用单例模式，全局集中管理所有文本词条，支持热切换与持久化配置。
"""

import json
import os

TRANSLATIONS = {
    "zh_CN": {
        # 主窗口
        "app_title": "万能钥匙 (UniversalKey) - 全网智能资源嗅探与搜索引擎 (商业旗舰版)",
        "omni_title": "🔑 万能钥匙极速接入（全自动智能识别：网址解析 / 影视搜剧 / 协议嗅探）",
        "omni_placeholder": "💡 随意输入：网页URL（如爱优腾/B站/各类影视站）、影视剧名称（如流浪地球/狂飙）、或磁力magnet链接...",
        "btn_omni": "⚡ 一键破译 / 极速搜索",
        "chk_force_browser": "强力穿透模式 (遇到特种 Cloudflare/极难防护站时勾选)",
        "chk_deep_dive": "🌊 全网深潜模式 (网盘暗搜+全球磁力+绝版冷门穿透)",
        "lbl_tip": "✨ 智能路由：自动判断网页或剧名，0 学习成本，内置秒级全网聚合节点与本地流媒体代理",
        
        # 过滤器
        "filter_group": "分类过滤",
        "chk_video": "🎬 影视流媒体 (在线秒播)",
        "chk_software": "💻 软件应用 (安装包/工具)",
        "chk_doc": "📄 办公文档 (简历/合同/PPT)",
        "chk_image": "🖼 图像相册 (海报/壁纸)",
        "btn_select_all": "全选显示项",
        "btn_deselect_all": "取消全选",
        
        # 表格
        "table_group": "已整理资源列表 (点击绿色按钮立即秒播)",
        "col_check": "勾选",
        "col_name": "资源名称 / 剧集",
        "col_type": "类型说明",
        "col_size": "资源大小",
        "col_action": "快速操作",
        "col_url": "资源链接",
        
        # 表格分类说明
        "cat_video": "🎬 高清视频",
        "cat_video_stream": "🎬 在线影视 (秒开即播/可下载)",
        "cat_software": "💻 软件应用",
        "cat_document": "📄 办公文档",
        "cat_pan_drive": "☁️ 网盘转存 (免限速原画)",
        "cat_magnet": "🧲 磁力链接 (P2P高速)",
        "cat_audio": "🎵 音频资源",
        "cat_image": "🖼 图像海报",
        "cat_other": "其他资源",
        
        # 表格内操作按钮
        "btn_play": "▶ 播放",
        "btn_preview": "🔍 预览",
        "btn_download_single": "⬇ 下载",
        "btn_pan": "☁️ 转存网盘",
        "btn_magnet": "🧲 磁力直通",
        
        # 统计栏
        "stats_template": "📊 统计信息: 当前共 {total} 个资源 | 已选择 {selected} 项 | 预估总大小: {size}",
        
        # 底部操作
        "bottom_group": "下载与本地文件整理",
        "lbl_save_dir": "保存目录:",
        "btn_change_dir": "选择文件夹",
        "btn_open_dir": "📂 打开下载文件夹",
        "btn_start_download": "⬇ 批量下载勾选资源并合成完整MP4",
        "log_group": "运行日志",
        
        # 弹窗与提示
        "msg_tip": "提示",
        "msg_input_empty": "请输入网址、电影名称或磁力链接！",
        "msg_download_done": "下载完成",
        "msg_download_done_video": "已成功将所有切片合成整理为完整可播放视频：\n{file}\n\n是否立即打开观看？",
        "msg_download_done_general": "所选资源已下载完成，保存目录：\n{dir}",
        "msg_copy_success": "已成功复制到剪贴板！",
        "msg_no_selected": "请先勾选需要下载的资源项！",
        "pan_copied_title": "网盘链接与提取码已就绪",
        "pan_copied_msg": "已复制网盘链接与提取码到剪贴板！\n链接: {url}\n提取码: {pwd}\n即将为您自动打开浏览器...",
        "magnet_copied_title": "磁力链接已复制",
        "magnet_copied_msg": "已成功将磁力链接 (magnet:?...) 复制到剪贴板！\n您可以直接粘贴至迅雷、BitComet、Aria2 或客户端下载。",
        
        # 播放弹窗
        "player_title": "🎬 极速硬件播放: {title}",
        "player_status_loading": "⚡ 正在建立硬件加速流媒体通道...",
        "player_status_playing": "🟢 极速硬件加速解码中 (秒开出画)",
        "player_status_error": "⚠ 原生解码提示: {err} (可点击右上角调用外部播放器)",
        "player_btn_sys": "🖥 调用外部播放器 (IINA / QuickTime / VLC)",
        "player_btn_copy": "📋 复制流地址",
        "player_fullscreen": "⛶ 全屏",
        "player_exit_fullscreen": "🗗 退出全屏",
        
        # 预览弹窗
        "preview_title": "🔍 资源深度核验与穿透预览: {title}",
        "preview_type": "资源类型: {cat} | 格式后缀: .{ext} | 检索来源: {source}",
        "preview_web_loading": "🌐 正在建立无痕安全沙箱并实时渲染原网视口...",
        "preview_found_link": "🎯 自动穿透提取出真实文件直链: 《{title}》 (.{ext})",
        "preview_btn_found_down": "⬇ 立即下载穿透直链",
        "preview_btn_browser": "🌐 外部浏览器打开",
        "preview_btn_copy": "📋 复制链接",
        "preview_btn_toggle": "🔄 切换视图",
        "preview_btn_down": "⬇ 确认正是所需，立即下载",
        "preview_btn_close": "关闭",
        "preview_img_loading": "⏳ 正在载入高清资源样张大图...",
        "preview_img_tip": "📄 资源样张预览已生成 (可直接点击下方【立即下载/打开】获取原件)",
        
        # 语言切换
                # 额外完善词条
        "size_unknown": "未知大小",
        "size_hd_stream": "高清流 (~800MB-1.2GB)",
        "dialog_choose_dir": "选择保存目录",
        "msg_success": "完成",
        "preview_link_copied": "资源直链已成功复制到剪贴板！",
        "stream_link_copied": "真实流媒体链接已复制到剪贴板！",
        "category_unknown": "未知",
        "source_default": "全网源",
        "attachment_pkg": "附件包",
        "preview_found_status": "✨ 穿透引擎已为您在目标页面中锁定 {count} 个直出文件，可直接点击下方绿钮高速下载！",
        "preview_rendering_target": "🌐 正在内嵌渲染目标网页环境: {url}",
        "preview_direct_url_tip": "📄 资源地址: {url}\n(可直接点击下方【立即下载】)",
        "log_start_url": "=== [万能钥匙] 识别为网页目标，启动全息深度嗅探: {url} ===",
        "log_start_p2p": "=== [万能钥匙] 识别为 P2P / 磁力协议，正在直链载入 ===",
        "log_start_search": "=== [万能钥匙] 识别为全网资源关键词，启动矩阵并发检索: 《{keyword}》 ===",
        "log_scan_done": "整理完成！共整理出 {count} 条可用资源。",
        "log_download_done": "=== 下载与合成已完成，已自动整理为标准MP4文件！===",
        "log_open_player": "正在唤醒极速播放窗口: {title}",
        "log_open_preview": "正在打开资源预览: {title}",
        "lang_name": "简体中文",
        "lbl_lang": "语言 / Language:"
    },

    "en_US": {
        # MainWindow
        "app_title": "UniversalKey - All-in-One Smart Media & Resource Engine (Enterprise Edition)",
        "omni_title": "🔑 Universal Engine (Auto Detection: URL Parser / Media Finder / Protocol Sniffer)",
        "omni_placeholder": "💡 Enter URL (YouTube/Bilibili/Streaming Sites), Movie Title, or Magnet Link...",
        "btn_omni": "⚡ One-Click Parse / Search",
        "chk_force_browser": "Deep Penetration Mode (For Cloudflare / Complex Protected Sites)",
        "chk_deep_dive": "🌊 Deep Dive Mode (Pan Cloud + Global Magnet/DHT + Rare Titles)",
        "lbl_tip": "✨ Smart Routing: Automatic media type detection, zero learning curve, local loopback proxy",
        
        # Filters
        "filter_group": "Filter Categories",
        "chk_video": "🎬 Video Streaming (Instant Play)",
        "chk_software": "💻 Software / Apps (Installers)",
        "chk_doc": "📄 Documents (Word/PDF/Templates)",
        "chk_image": "🖼 Images & Wallpapers",
        "btn_select_all": "Select All",
        "btn_deselect_all": "Deselect All",
        
        # Table
        "table_group": "Discovered Resources (Click Green Button to Play)",
        "col_check": "Select",
        "col_name": "Resource Name / Title",
        "col_type": "Category",
        "col_size": "Size",
        "col_action": "Quick Action",
        "col_url": "Direct Link",
        
        # Category Descriptions
        "cat_video": "🎬 HD Video",
        "cat_video_stream": "🎬 Live Stream (Instant / Downloadable)",
        "cat_software": "💻 Software Application",
        "cat_document": "📄 Office Document",
        "cat_pan_drive": "☁️ Cloud Drive (Fast & Original)",
        "cat_magnet": "🧲 Magnet Link (P2P High-Speed)",
        "cat_audio": "🎵 Audio Resource",
        "cat_image": "🖼 Image / Poster",
        "cat_other": "Other Resource",
        
        # In-table Action Buttons
        "btn_play": "▶ Play",
        "btn_preview": "🔍 Preview",
        "btn_download_single": "⬇ Download",
        "btn_pan": "☁️ Cloud Drive",
        "btn_magnet": "🧲 Magnet Direct",
        
        # Stats
        "stats_template": "📊 Statistics: {total} items found | {selected} selected | Estimated size: {size}",
        
        # Bottom Actions
        "bottom_group": "Download & Output Management",
        "lbl_save_dir": "Save Path:",
        "btn_change_dir": "Browse Folder",
        "btn_open_dir": "📂 Open Folder",
        "btn_start_download": "⬇ Download Selected Items & Merge to MP4",
        "log_group": "Activity Log",
        
        # Dialogs & Prompts
        "msg_tip": "Notice",
        "msg_input_empty": "Please enter a URL, movie name, or magnet link!",
        "msg_download_done": "Download Completed",
        "msg_download_done_video": "Successfully synthesized video:\n{file}\n\nDo you want to play it now?",
        "msg_download_done_general": "Selected resources downloaded to:\n{dir}",
        "msg_copy_success": "Link copied to clipboard!",
        "msg_no_selected": "Please select at least one item to download!",
        "pan_copied_title": "Cloud Link & Passcode Ready",
        "pan_copied_msg": "Link and passcode copied to clipboard!\nURL: {url}\nCode: {pwd}\nOpening browser...",
        "magnet_copied_title": "Magnet Link Copied",
        "magnet_copied_msg": "Magnet link copied to clipboard!\nYou can paste it directly into Thunder, BitComet, qBittorrent, or Aria2.",
        
        # Player Dialog
        "player_title": "🎬 Hardware Accelerated Player: {title}",
        "player_status_loading": "⚡ Establishing hardware accelerated stream...",
        "player_status_playing": "🟢 Playing smoothly with hardware decoding",
        "player_status_error": "⚠ Decoder notice: {err} (External player available at top-right)",
        "player_btn_sys": "🖥 External Player (IINA / VLC / QuickTime)",
        "player_btn_copy": "📋 Copy Stream URL",
        "player_fullscreen": "⛶ Fullscreen",
        "player_exit_fullscreen": "🗗 Exit Fullscreen",
        
        # Preview Dialog
        "preview_title": "🔍 Deep Inspection & Preview: {title}",
        "preview_type": "Category: {cat} | Extension: .{ext} | Source: {source}",
        "preview_web_loading": "🌐 Initializing secure sandbox viewport...",
        "preview_found_link": "🎯 Direct download file extracted: 《{title}》 (.{ext})",
        "preview_btn_found_down": "⬇ Download Extracted File",
        "preview_btn_browser": "🌐 Open in Browser",
        "preview_btn_copy": "📋 Copy Link",
        "preview_btn_toggle": "🔄 Switch View",
        "preview_btn_down": "⬇ Download This Resource",
        "preview_btn_close": "Close",
        "preview_img_loading": "⏳ Loading high-resolution preview sample...",
        "preview_img_tip": "📄 Sample preview generated (Click Download below to get original)",
        
        # Language
                # Extra items
        "size_unknown": "Unknown size",
        "size_hd_stream": "HD Stream (~800MB-1.2GB)",
        "dialog_choose_dir": "Select Download Directory",
        "msg_success": "Success",
        "preview_link_copied": "Direct link copied to clipboard!",
        "stream_link_copied": "Stream URL copied to clipboard!",
        "category_unknown": "Unknown",
        "source_default": "Global Sources",
        "attachment_pkg": "Attachment",
        "preview_found_status": "✨ Engine detected {count} direct files in page. Click green button below to download!",
        "preview_rendering_target": "🌐 Rendering target page environment: {url}",
        "preview_direct_url_tip": "📄 Resource URL: {url}\n(Click Download below)",
        "log_start_url": "=== [UniversalKey] URL detected, starting deep sniffer: {url} ===",
        "log_start_p2p": "=== [UniversalKey] P2P / Magnet protocol detected, loading direct stream ===",
        "log_start_search": "=== [UniversalKey] Keyword detected, starting parallel matrix search: 《{keyword}》 ===",
        "log_scan_done": "Done! Organized {count} available resources.",
        "log_download_done": "=== Download & merge complete, formatted as standard MP4! ===",
        "log_open_player": "Opening hardware player: {title}",
        "log_open_preview": "Opening resource preview: {title}",
        "lang_name": "English",
        "lbl_lang": "Language / 语言:"
    },

    "zh_TW": {
        # 繁體中文
        "app_title": "萬能鑰匙 (UniversalKey) - 全網智慧資源嗅探與搜尋引擎 (商業旗艦版)",
        "omni_title": "🔑 萬能鑰匙極速接入（全自動智慧識別：網址解析 / 影視搜尋 / 協議嗅探）",
        "omni_placeholder": "💡 隨意輸入：網頁URL、影視劇名稱、或磁力magnet連結...",
        "btn_omni": "⚡ 一鍵破譯 / 極速搜尋",
        "chk_force_browser": "強力穿透模式 (遇到特種 Cloudflare/極難防護站時勾選)",
        "chk_deep_dive": "🌊 全網深潛模式 (網盤暗搜+全球磁力+絕版冷門穿透)",
        "lbl_tip": "✨ 智慧路由：自動判斷網頁或劇名，0 學習成本，內建秒級全網聚合節點與本地流媒體代理",
        
        # 過濾器
        "filter_group": "分類過濾",
        "chk_video": "🎬 影視串流 (線上秒播)",
        "chk_software": "💻 軟體應用 (安裝包/工具)",
        "chk_doc": "📄 辦公文檔 (簡歷/合約/PPT)",
        "chk_image": "🖼 圖像相簿 (海报/桌布)",
        "btn_select_all": "全選顯示項",
        "btn_deselect_all": "取消全選",
        
        # 表格
        "table_group": "已整理資源列表 (點擊綠色按鈕立即秒播)",
        "col_check": "勾選",
        "col_name": "資源名稱 / 劇集",
        "col_type": "類型說明",
        "col_size": "資源大小",
        "col_action": "快速操作",
        "col_url": "資源連結",
        
        # 表格分類說明
        "cat_video": "🎬 高清影片",
        "cat_video_stream": "🎬 線上影視 (秒開即播/可下載)",
        "cat_software": "💻 軟體應用",
        "cat_document": "📄 辦公文檔",
        "cat_pan_drive": "☁️ 網盤轉存 (免限速原畫)",
        "cat_magnet": "🧲 磁力連結 (P2P高速)",
        "cat_audio": "🎵 音訊資源",
        "cat_image": "🖼 圖像海報",
        "cat_other": "其他資源",
        
        # 按鈕
        "btn_play": "▶ 播放",
        "btn_preview": "🔍 預覽",
        "btn_download_single": "⬇ 下載",
        "btn_pan": "☁️ 轉存網盤",
        "btn_magnet": "🧲 磁力直通",
        
        # 統計欄
        "stats_template": "📊 統計資訊: 目前共 {total} 個資源 | 已選擇 {selected} 項 | 預估總大小: {size}",
        
        # 底部操作
        "bottom_group": "下載與本機檔案整理",
        "lbl_save_dir": "儲存目錄:",
        "btn_change_dir": "選擇資料夾",
        "btn_open_dir": "📂 開啟下載資料夾",
        "btn_start_download": "⬇ 批次下載勾選資源並合成完整MP4",
        "log_group": "執行日誌",
        
        # 提示
        "msg_tip": "提示",
        "msg_input_empty": "請輸入網址、電影名稱或磁力連結！",
        "msg_download_done": "下載完成",
        "msg_download_done_video": "已成功將所有切片合成整理為完整可播放影片：\n{file}\n\n是否立即打開觀看？",
        "msg_download_done_general": "所選資源已下載完成，儲存目錄：\n{dir}",
        "msg_copy_success": "已成功複製到剪貼簿！",
        "msg_no_selected": "請先勾選需要下載的資源項！",
        "pan_copied_title": "網盤連結與提取碼已就緒",
        "pan_copied_msg": "已複製網盤連結與提取碼至剪貼簿！\n連結: {url}\n提取碼: {pwd}\n即將自動開啟瀏覽器...",
        "magnet_copied_title": "磁力連結已複製",
        "magnet_copied_msg": "已成功將磁力連結複製至剪貼簿！\n您可以直接貼至迅雷、BitComet、Aria2 進行下載。",
        
        # 播放彈窗
        "player_title": "🎬 極速硬體播放: {title}",
        "player_status_loading": "⚡ 正在建立硬體加速流媒體通道...",
        "player_status_playing": "🟢 極速硬體加速解碼中 (秒開出畫)",
        "player_status_error": "⚠ 原生解碼提示: {err} (可點擊右上角呼叫外部播放器)",
        "player_btn_sys": "🖥 呼叫外部播放器 (IINA / QuickTime / VLC)",
        "player_btn_copy": "📋 複製串流網址",
        "player_fullscreen": "⛶ 全螢幕",
        "player_exit_fullscreen": "🗗 退出全螢幕",
        
        # 預覽彈窗
        "preview_title": "🔍 資源深度核驗與穿透預覽: {title}",
        "preview_type": "資源類型: {cat} | 格式後綴: .{ext} | 檢索來源: {source}",
        "preview_web_loading": "🌐 正在建立無痕安全沙箱並即時渲染原網視窗...",
        "preview_found_link": "🎯 自動穿透提取出真實檔案直鏈: 《{title}》 (.{ext})",
        "preview_btn_found_down": "⬇ 立即下載穿透直鏈",
        "preview_btn_browser": "🌐 外部瀏覽器打開",
        "preview_btn_copy": "📋 複製連結",
        "preview_btn_toggle": "🔄 切換視圖",
        "preview_btn_down": "⬇ 確認正是所需，立即下載",
        "preview_btn_close": "關閉",
        "preview_img_loading": "⏳ 正在載入高清資源樣張大圖...",
        "preview_img_tip": "📄 資源樣張預覽已生成 (可直接點擊下方【立即下載/打開】獲取原件)",
        
        # 語言
                # 額外完善詞條
        "size_unknown": "未知大小",
        "size_hd_stream": "高清串流 (~800MB-1.2GB)",
        "dialog_choose_dir": "選擇儲存目錄",
        "msg_success": "完成",
        "preview_link_copied": "資源直鏈已成功複製到剪貼簿！",
        "stream_link_copied": "真實流媒體連結已複製到剪貼簿！",
        "category_unknown": "未知",
        "source_default": "全網源",
        "attachment_pkg": "附件包",
        "preview_found_status": "✨ 穿透引擎已為您在目標頁面中鎖定 {count} 個直出檔案，可直接點擊下方綠鈕高速下載！",
        "preview_rendering_target": "🌐 正在內嵌渲染目標網頁環境: {url}",
        "preview_direct_url_tip": "📄 資源位址: {url}\n(可直接點擊下方【立即下載】)",
        "log_start_url": "=== [萬能鑰匙] 識別為網頁目標，啟動全息深度嗅探: {url} ===",
        "log_start_p2p": "=== [萬能鑰匙] 識別為 P2P / 磁力協議，正在直鏈載入 ===",
        "log_start_search": "=== [萬能鑰匙] 識別為全網資源關鍵詞，啟動矩陣並發檢索: 《{keyword}》 ===",
        "log_scan_done": "整理完成！共整理出 {count} 條可用資源。",
        "log_download_done": "=== 下載與合成已完成，已自動整理為標準MP4檔案！===",
        "log_open_player": "正在喚醒極速播放視窗: {title}",
        "log_open_preview": "正在打開資源預覽: {title}",
        "lang_name": "繁體中文",
        "lbl_lang": "語言 / Language:"
    },

    "ja_JP": {
        # 日本語
        "app_title": "万能マスター (UniversalKey) - スマートメディア＆リソース検索エンジン",
        "omni_title": "🔑 万能エンジン（自動検出：URL解析 / 動画検索 / プロトコル嗅覚）",
        "omni_placeholder": "💡 URL（YouTube/Bilibili/動画配信サイト）、タイトル、またはMagnetリンクを入力...",
        "btn_omni": "⚡ 解析 / 高速検索",
        "chk_force_browser": "ディープペネトレーションモード（Cloudflare保護サイト用）",
        "chk_deep_dive": "🌊 ディープダイブモード (クラウド+マグネット+レア作品発掘)",
        "lbl_tip": "✨ スマートルーティング：自動メディア検出、ローカルプロキシ搭載、ゼロ学習コスト",
        
        # フィルター
        "filter_group": "カテゴリ絞り込み",
        "chk_video": "🎬 動画ストリーミング (即時再生)",
        "chk_software": "💻 ソフトウェア (インストーラー)",
        "chk_doc": "📄 ドキュメント (Word/PDF/テンプレート)",
        "chk_image": "🖼 画像 / 壁紙",
        "btn_select_all": "すべて選択",
        "btn_deselect_all": "選択解除",
        
        # テーブル
        "table_group": "検出リソース一覧（緑のボタンで即時再生）",
        "col_check": "選択",
        "col_name": "リソース名 / タイトル",
        "col_type": "カテゴリ",
        "col_size": "サイズ",
        "col_action": "アクション",
        "col_url": "リンク",
        
        # カテゴリ説明
        "cat_video": "🎬 HD動画",
        "cat_video_stream": "🎬 ストリーム (即時再生/DL可能)",
        "cat_software": "💻 アプリケーション",
        "cat_document": "📄 ドキュメント",
        "cat_pan_drive": "☁️ クラウド共有 (原画保存)",
        "cat_magnet": "🧲 マグネットリンク (P2P高速)",
        "cat_audio": "🎵 音楽 / 音声",
        "cat_image": "🖼 画像ポスター",
        "cat_other": "その他",
        
        # ボタン
        "btn_play": "▶ 再生",
        "btn_preview": "🔍 プレビュー",
        "btn_download_single": "⬇ ダウンロード",
        "btn_pan": "☁️ クラウドへ保存",
        "btn_magnet": "🧲 マグネット取得",
        
        # 統計
        "stats_template": "📊 統計: 合計 {total} 件 | 選択済み {selected} 件 | 推定サイズ: {size}",
        
        # 底部
        "bottom_group": "ダウンロード設定とファイル管理",
        "lbl_save_dir": "保存先:",
        "btn_change_dir": "フォルダ選択",
        "btn_open_dir": "📂 フォルダを開く",
        "btn_start_download": "⬇ 選択項目を一括ダウンロードしてMP4に結合",
        "log_group": "実行ログ",
        
        # ダイアログ
        "msg_tip": "ヒント",
        "msg_input_empty": "URL、動画タイトル、またはMagnetリンクを入力してください！",
        "msg_download_done": "完了",
        "msg_download_done_video": "MP4動画の結合が完了しました:\n{file}\n\n今すぐ再生しますか？",
        "msg_download_done_general": "ダウンロード完了。保存先:\n{dir}",
        "msg_copy_success": "クリップボードにコピーしました！",
        "msg_no_selected": "ダウンロードするリソースを選択してください！",
        "pan_copied_title": "クラウドURLとパスコード取得完了",
        "pan_copied_msg": "URLとパスコードをクリップボードにコピーしました！\nURL: {url}\nコード: {pwd}\nブラウザを開きます...",
        "magnet_copied_title": "マグネットリンクをコピーしました",
        "magnet_copied_msg": "マグネットリンクをクリップボードにコピーしました！\nBitTorrentやThunderなどに貼り付けてダウンロードできます。",
        
        # プレイヤー
        "player_title": "🎬 高速ハードウェア再生: {title}",
        "player_status_loading": "⚡ ハードウェアストリーミングチャンネルを確立中...",
        "player_status_playing": "🟢 ハードウェアアクセラレーションで再生中",
        "player_status_error": "⚠ デコード通知: {err} (外部プレイヤーで再生可能)",
        "player_btn_sys": "🖥 外部プレイヤーで再生 (IINA / VLC / QuickTime)",
        "player_btn_copy": "📋 URLをコピー",
        "player_fullscreen": "⛶ フルスクリーン",
        "player_exit_fullscreen": "🗗 全画面解除",
        
        # プレビュー
        "preview_title": "🔍 リソース詳細プレビュー: {title}",
        "preview_type": "カテゴリ: {cat} | 拡張子: .{ext} | ソース: {source}",
        "preview_web_loading": "🌐 サンドボックスビューポートをレンダリング中...",
        "preview_found_link": "🎯 直接ダウンロードリンクを検出: 《{title}》 (.{ext})",
        "preview_btn_found_down": "⬇ 検出ファイルをダウンロード",
        "preview_btn_browser": "🌐 ブラウザで開く",
        "preview_btn_copy": "📋 リンクをコピー",
        "preview_btn_toggle": "🔄 表示切替",
        "preview_btn_down": "⬇ このリソースをダウンロード",
        "preview_btn_close": "閉じる",
        "preview_img_loading": "⏳ 高画質プレビュー画像を読み込み中...",
        "preview_img_tip": "📄 プレビューを生成しました（下のダウンロードボタンで原本を取得可能）",
        
        # 言語
                # 追加項目
        "size_unknown": "不明なサイズ",
        "size_hd_stream": "HDストリーム (~800MB-1.2GB)",
        "dialog_choose_dir": "保存先フォルダの選択",
        "msg_success": "完了",
        "preview_link_copied": "ダイレクトリンクをクリップボードにコピーしました！",
        "stream_link_copied": "ストリームURLをクリップボードにコピーしました！",
        "category_unknown": "不明",
        "source_default": "グローバル検索",
        "attachment_pkg": "添付ファイル",
        "preview_found_status": "✨ 対象ページから {count} 個の直接ファイルを検出しました。下のボタンから高速ダウンロード可能！",
        "preview_rendering_target": "🌐 対象ウェブページを描画中: {url}",
        "preview_direct_url_tip": "📄 リソースURL: {url}\n(下の【ダウンロード】ボタンをクリック)",
        "log_start_url": "=== [UniversalKey] Webページを識別、ディープスニッフィングを開始: {url} ===",
        "log_start_p2p": "=== [UniversalKey] P2P / Magnetプロトコルを検出、直接読み込み中 ===",
        "log_start_search": "=== [UniversalKey] 検索キーワードを認識、マトリックス検索開始: 《{keyword}》 ===",
        "log_scan_done": "完了！利用可能なリソース {count} 件を整理しました。",
        "log_download_done": "=== ダウンロードおよびMP4結合が完了しました！===",
        "log_open_player": "高速プレーヤーを起動中: {title}",
        "log_open_preview": "リソースプレビューを開いています: {title}",
        "lang_name": "日本語",
        "lbl_lang": "言語 / Language:"
    },

    "ko_KR": {
        # 한국어
        "app_title": "만능 열쇠 (UniversalKey) - 스마트 미디어 및 리소스 검색 엔진 (상용판)",
        "omni_title": "🔑 만능 열쇠 (자동 감지: URL 분석 / 미디어 검색 / 프로토콜 스니퍼)",
        "omni_placeholder": "💡 웹페이지 URL, 영화/드라마 제목, 또는 마그넷 링크를 입력하세요...",
        "btn_omni": "⚡ 원클릭 분석 / 검색",
        "chk_force_browser": "강력 침투 모드 (Cloudflare 등 보호 사이트 전용)",
        "chk_deep_dive": "🌊 딥 다이브 모드 (클라우드+마그넷+희귀/절판 리소스 탐색)",
        "lbl_tip": "✨ 스마트 라우팅: 자동 미디어 판별, 로컬 프록시 내장, 쉬운 사용성",
        
        # 필터
        "filter_group": "카테고리 필터",
        "chk_video": "🎬 비디오 스트리밍 (즉시 재생)",
        "chk_software": "💻 소프트웨어 (설치 프로그램)",
        "chk_doc": "📄 오피스 문서 (이력서/서식/PPT)",
        "chk_image": "🖼 이미지 / 배경화면",
        "btn_select_all": "모두 선택",
        "btn_deselect_all": "선택 해제",
        
        # 테이블
        "table_group": "정리된 리소스 목록 (녹색 버튼 클릭 시 즉시 재생)",
        "col_check": "선택",
        "col_name": "리소스 이름 / 제목",
        "col_type": "유형",
        "col_size": "크기",
        "col_action": "작업",
        "col_url": "다운로드 링크",
        
        # 카테고리 설명
        "cat_video": "🎬 HD 비디오",
        "cat_video_stream": "🎬 스트리밍 (즉시 재생/다운로드)",
        "cat_software": "💻 소프트웨어 응용 프로그램",
        "cat_document": "📄 문서 자료",
        "cat_pan_drive": "☁️ 클라우드 드라이브 (고속 원본)",
        "cat_magnet": "🧲 마그넷 링크 (P2P 고속)",
        "cat_audio": "🎵 오디오 리소스",
        "cat_image": "🖼 이미지 포스터",
        "cat_other": "기타 리소스",
        
        # 버튼
        "btn_play": "▶ 재생",
        "btn_preview": "🔍 미리보기",
        "btn_download_single": "⬇ 다운로드",
        "btn_pan": "☁️ 클라우드 저장",
        "btn_magnet": "🧲 마그넷 바로가기",
        
        # 통계
        "stats_template": "📊 통계: 총 {total} 개 항목 | {selected} 개 선택됨 | 예상 크기: {size}",
        
        # 하단
        "bottom_group": "다운로드 및 파일 관리",
        "lbl_save_dir": "저장 경로:",
        "btn_change_dir": "폴더 선택",
        "btn_open_dir": "📂 폴더 열기",
        "btn_start_download": "⬇ 선택 항목 일괄 다운로드 및 MP4 병합",
        "log_group": "실행 로그",
        
        # 알림
        "msg_tip": "알림",
        "msg_input_empty": "URL, 미디어 제목 또는 마그넷 링크를 입력하세요!",
        "msg_download_done": "완료",
        "msg_download_done_video": "MP4 비디오 병합이 완료되었습니다:\n{file}\n\n지금 재생하시겠습니까?",
        "msg_download_done_general": "다운로드가 완료되었습니다. 저장 경로:\n{dir}",
        "msg_copy_success": "클립보드에 복사되었습니다!",
        "msg_no_selected": "다운로드할 리소스를 선택해 주세요!",
        "pan_copied_title": "클라우드 링크 및 비밀번호 준비 완료",
        "pan_copied_msg": "링크와 비밀번호가 클립보드에 복사되었습니다!\nURL: {url}\n비밀번호: {pwd}\n브라우저를 엽니다...",
        "magnet_copied_title": "마그넷 링크 복사됨",
        "magnet_copied_msg": "마그넷 링크가 클립보드에 복사되었습니다!\n토렌트 클라이언트나 다운로더에 붙여넣어 다운로드할 수 있습니다.",
        
        # 플레이어
        "player_title": "🎬 하드웨어 가속 플레이어: {title}",
        "player_status_loading": "⚡ 하드웨어 스트리밍 채널 연결 중...",
        "player_status_playing": "🟢 하드웨어 가속으로 원활히 재생 중",
        "player_status_error": "⚠ 디코딩 알림: {err} (외부 플레이어로 재생 가능)",
        "player_btn_sys": "🖥 외부 플레이어로 재생 (IINA / VLC / QuickTime)",
        "player_btn_copy": "📋 스트림 링크 복사",
        "player_fullscreen": "⛶ 전체 화면",
        "player_exit_fullscreen": "🗗 전체 화면 해제",
        
        # 미리보기
        "preview_title": "🔍 리소스 정밀 검증 및 미리보기: {title}",
        "preview_type": "유형: {cat} | 확장자: .{ext} | 출처: {source}",
        "preview_web_loading": "🌐 샌드박스 뷰포트 렌더링 중...",
        "preview_found_link": "🎯 직접 다운로드 파일 발견: 《{title}》 (.{ext})",
        "preview_btn_found_down": "⬇ 발견된 파일 즉시 다운로드",
        "preview_btn_browser": "🌐 브라우저에서 열기",
        "preview_btn_copy": "📋 링크 복사",
        "preview_btn_toggle": "🔄 뷰 전환",
        "preview_btn_down": "⬇ 이 리소스 다운로드",
        "preview_btn_close": "닫기",
        "preview_img_loading": "⏳ 고해상도 미리보기 이미지 로드 중...",
        "preview_img_tip": "📄 미리보기가 생성되었습니다 (하단 다운로드 버튼으로 원본 저장)",
        
        # 언어
                # 추가 항목
        "size_unknown": "알 수 없는 크기",
        "size_hd_stream": "고화질 스트림 (~800MB-1.2GB)",
        "dialog_choose_dir": "저장 폴더 선택",
        "msg_success": "완료",
        "preview_link_copied": "다운로드 링크가 클립보드에 복사되었습니다!",
        "stream_link_copied": "스트림 URL이 클립보드에 복사되었습니다!",
        "category_unknown": "알 수 없음",
        "source_default": "글로벌 소스",
        "attachment_pkg": "첨부 파일",
        "preview_found_status": "✨ 페이지 내 {count} 개의 직접 다운로드 파일을 감지했습니다. 하단 녹색 버튼으로 즉시 다운로드 가능!",
        "preview_rendering_target": "🌐 대상 웹페이지 렌더링 중: {url}",
        "preview_direct_url_tip": "📄 리소스 주소: {url}\n(하단 【다운로드】 클릭)",
        "log_start_url": "=== [UniversalKey] 웹 URL 감지, 심층 스니핑 시작: {url} ===",
        "log_start_p2p": "=== [UniversalKey] P2P / 마그넷 프로토콜 감지, 직링크 로드 중 ===",
        "log_start_search": "=== [UniversalKey] 키워드 감지, 매트릭스 병렬 검색 시작: 《{keyword}》 ===",
        "log_scan_done": "완료! 사용 가능한 리소스 {count} 개가 정리되었습니다.",
        "log_download_done": "=== 다운로드 및 MP4 병합이 완료되었습니다! ===",
        "log_open_player": "플레이어 창 시작 중: {title}",
        "log_open_preview": "리소스 미리보기 여는 중: {title}",
        "lang_name": "한국어",
        "lbl_lang": "언어 / Language:"
    }
}

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".universalkey_config.json")


class I18nManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_manager()
        return cls._instance

    def _init_manager(self):
        self.current_lang = "zh_CN"
        self._listeners = []
        self._load_config()

    def _load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    lang = cfg.get("language", "zh_CN")
                    if lang in TRANSLATIONS:
                        self.current_lang = lang
        except Exception:
            pass

    def _save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"language": self.current_lang}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_supported_languages(self):
        """返回支持的语言代号与显示名称字典"""
        return [
            ("zh_CN", "🇨🇳 简体中文"),
            ("en_US", "🇺🇸 English"),
            ("zh_TW", "🇭🇰 繁體中文"),
            ("ja_JP", "🇯🇵 日本語"),
            ("ko_KR", "🇰🇷 한국어")
        ]

    def get_all_keys(self):
        """返回所有支持的词条键集合"""
        return set(TRANSLATIONS.get("zh_CN", {}).keys())

    def set_language(self, lang_code: str):
        if lang_code in TRANSLATIONS and lang_code != self.current_lang:
            self.current_lang = lang_code
            self._save_config()
            self._notify_listeners()

    def tr(self, key: str, **kwargs) -> str:
        """获取翻译文本并格式化参数"""
        lang_dict = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["zh_CN"])
        text = lang_dict.get(key, TRANSLATIONS["zh_CN"].get(key, key))
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text

    def register_listener(self, callback):
        """注册语言改变时的全局重新渲染回调"""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def unregister_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self):
        for cb in self._listeners:
            try:
                cb()
            except Exception:
                pass


# 全局单例函数
_I18N = I18nManager()

def tr(key: str, **kwargs) -> str:
    return _I18N.tr(key, **kwargs)

def get_i18n() -> I18nManager:
    return _I18N
