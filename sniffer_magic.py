"""
文件指纹与魔数（Magic Number）识别模块
用于穿透网站的扩展名伪装（例如将 mp4 改名为 png，将 pdf 改名为 dat 等）
"""

MAGIC_SIGNATURES = [
    # 传统与现代视频 / 媒体
    (b"ftyp", 4, "video", "mp4"),
    (b"\x1a\x45\xdf\xa3", 0, "video", "mkv"),
    (b"FLV\x01", 0, "video", "flv"),
    (b"RIFF", 0, "video", "avi"),
    (b"#EXTM3U", 0, "video_stream", "m3u8"),
    (b"\x30\x26\xb2\x75\x8e\x66\xcf\x11", 0, "video", "wmv"),
    (b".RMF", 0, "video", "rmvb"),
    (b"FWS", 0, "video", "swf"),
    (b"CWS", 0, "video", "swf"),

    # 音频
    (b"ID3", 0, "audio", "mp3"),
    (b"fLaC", 0, "audio", "flac"),
    (b"OggS", 0, "audio", "ogg"),

    # 图片
    (b"\xff\xd8\xff", 0, "image", "jpg"),
    (b"\x89PNG\r\n\x1a\n", 0, "image", "png"),
    (b"GIF87a", 0, "image", "gif"),
    (b"GIF89a", 0, "image", "gif"),
    (b"BM", 0, "image", "bmp"),
    (b"II*\x00", 0, "image", "tiff"),

    # 文档 / 压缩包 / 种子
    (b"%PDF-", 0, "document", "pdf"),
    (b"PK\x03\x04", 0, "archive_or_doc", "zip"),
    (b"Rar!\x1a\x07", 0, "archive", "rar"),
    (b"7z\xbc\xaf\x27\x1c", 0, "archive", "7z"),
    (b"d8:announce", 0, "document", "torrent"),
]

MIME_MAP = {
    # 视频
    "video/mp4": ("video", "mp4"),
    "video/webm": ("video", "webm"),
    "video/x-flv": ("video", "flv"),
    "video/x-matroska": ("video", "mkv"),
    "video/quicktime": ("video", "mov"),
    "video/x-msvideo": ("video", "avi"),
    "video/x-ms-wmv": ("video", "wmv"),
    "video/vnd.rn-realvideo": ("video", "rmvb"),
    "video/3gpp": ("video", "3gp"),
    "application/x-mpegurl": ("video_stream", "m3u8"),
    "application/vnd.apple.mpegurl": ("video_stream", "m3u8"),
    "video/mp2t": ("video_segment", "ts"),
    "application/x-shockwave-flash": ("video", "swf"),

    # 音频
    "audio/mpeg": ("audio", "mp3"),
    "audio/mp3": ("audio", "mp3"),
    "audio/wav": ("audio", "wav"),
    "audio/x-wav": ("audio", "wav"),
    "audio/aac": ("audio", "aac"),
    "audio/ogg": ("audio", "ogg"),
    "audio/flac": ("audio", "flac"),
    "audio/x-m4a": ("audio", "m4a"),
    "audio/x-ms-wma": ("audio", "wma"),

    # 图片
    "image/jpeg": ("image", "jpg"),
    "image/png": ("image", "png"),
    "image/gif": ("image", "gif"),
    "image/webp": ("image", "webp"),
    "image/svg+xml": ("image", "svg"),
    "image/bmp": ("image", "bmp"),
    "image/x-icon": ("image", "ico"),

    # 文档
    "application/pdf": ("document", "pdf"),
    "application/msword": ("document", "doc"),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ("document", "docx"),
    "application/vnd.ms-excel": ("document", "xls"),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ("document", "xlsx"),
    "application/vnd.ms-powerpoint": ("document", "ppt"),
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ("document", "pptx"),
    "application/zip": ("archive", "zip"),
    "application/x-rar-compressed": ("archive", "rar"),
    "application/x-7z-compressed": ("archive", "7z"),
    "application/x-bittorrent": ("document", "torrent"),
}

def detect_by_magic(sample_bytes: bytes):
    if not sample_bytes or len(sample_bytes) < 4:
        return None, None

    if sample_bytes[:4] == b"RIFF" and len(sample_bytes) >= 12 and sample_bytes[8:12] == b"WEBP":
        return "image", "webp"
    if sample_bytes[:4] == b"RIFF" and len(sample_bytes) >= 12 and sample_bytes[8:12] == b"AVI ":
        return "video", "avi"

    for sig, offset, category, ext in MAGIC_SIGNATURES:
        sig_len = len(sig)
        if len(sample_bytes) >= offset + sig_len:
            if sample_bytes[offset:offset + sig_len] == sig:
                return category, ext

    return None, None

def identify_resource(content_type: str, url: str, sample_bytes: bytes = None):
    # 1. 优先通过 Magic Bytes 二进制判定真实类型（穿透扩展名伪装）
    if sample_bytes:
        cat, ext = detect_by_magic(sample_bytes)
        if cat:
            return cat, ext

    # 2. 通过 Content-Type 判定
    if content_type:
        clean_ct = content_type.split(";")[0].strip().lower()
        if clean_ct in MIME_MAP:
            return MIME_MAP[clean_ct]

        if clean_ct.startswith("video/"):
            return "video", clean_ct.split("/")[-1]
        if clean_ct.startswith("image/"):
            return "image", clean_ct.split("/")[-1]
        if clean_ct.startswith("audio/"):
            return "audio", clean_ct.split("/")[-1]

    # 3. 回退通过 URL 特征与扩展名判定
    if url.lower().startswith("magnet:"):
        return "magnet", "magnet"
    if url.lower().startswith("ed2k://"):
        return "document", "ed2k"
    if url.lower().startswith("thunder://"):
        return "document", "thunder"

    # 网盘转存链接识别
    pan_domains = ["pan.quark.cn", "pan.baidu.com", "123pan.com", "lanzou", "ctfile.com", "aliyundrive.com", "drive.uc.cn", "mypikpak.com"]
    if any(pd in url.lower() for pd in pan_domains):
        return "pan_drive", "pan"

    url_lower = url.lower().split("?")[0]
    for ext in [".m3u8", ".mp4", ".flv", ".f4v", ".webm", ".avi", ".mkv", ".mov", ".wmv", ".rmvb", ".rm", ".3gp", ".asf", ".m4v", ".ts", ".swf"]:
        if url_lower.endswith(ext):
            return "video_stream" if ext == ".m3u8" else "video", ext.strip(".")

    for ext in [".mp3", ".wav", ".aac", ".ogg", ".flac", ".m4a", ".wma", ".ape"]:
        if url_lower.endswith(ext):
            return "audio", ext.strip(".")

    for ext in [".exe", ".dmg", ".pkg", ".apk", ".msi", ".deb", ".rpm", ".ipa", ".appimage"]:
        if url_lower.endswith(ext):
            return "software", ext.strip(".")

    for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg", ".ico", ".tiff"]:
        if url_lower.endswith(ext):
            return "image", ext.strip(".")

    for ext in [".pdf", ".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt", ".txt", ".csv", ".zip", ".rar", ".7z", ".tar", ".gz", ".iso", ".torrent"]:
        if url_lower.endswith(ext):
            return "document", ext.strip(".")

    return "other", "bin"

