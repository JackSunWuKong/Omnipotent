import os
from downloader import Downloader
from main_ui import open_file_with_system_player

save_dir = os.path.join(os.path.expanduser("~"), "Downloads", "UniversalScraper")
dl = Downloader(save_dir)

# 抓取一个标准 3 秒公共 m3u8 切片合成测试
sample_m3u8 = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"
ok, target_path = dl.download_m3u8(sample_m3u8, referer="", suggested_name="测试成功播放的电影.mp4")
print("Download result:", ok, target_path)
if ok:
    print(f"✓ 文件真实生成: {target_path} (大小: {os.path.getsize(target_path)} 字节)")
    open_file_with_system_player(target_path)
