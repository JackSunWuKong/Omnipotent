import sys, os, subprocess

def main():
    print('========================================================')
    print('      OmniFinder (万象探索) - 自动打包工具')
    print('========================================================')
    print()

    # 1. 检查并安装依赖
    print('[1/2] 正在检查并安装所需组件...')
    pkgs = ['pyinstaller', 'PyQt5', 'PyQtWebEngine', 'httpx', 'beautifulsoup4', 'yt-dlp', 'requests']
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-i', 'https://mirrors.aliyun.com/pypi/simple/', '--trusted-host', 'mirrors.aliyun.com'] + pkgs)
    except Exception as e:
        print('[警告] 依赖安装提示:', e)

    # 2. 调用 pyinstaller 打包
    print()
    print('[2/2] 正在生成独立的 Windows 应用程序 (exe)...')
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--noconfirm',
        '--onefile',
        '--windowed',
        '--name=OmniFinder',
        '--add-data=sniffer_magic.py;.',
        '--add-data=downloader.py;.',
        '--add-data=sniffer_engine.py;.',
        '--add-data=video_extractor.py;.',
        '--add-data=vip_parser.py;.',
        '--add-data=resource_searcher.py;.',
        '--add-data=player_server.py;.',
        '--add-data=i18n.py;.',
        '--add-data=assets;assets',
        'main_ui.py'
    ]
    ret = subprocess.call(cmd)
    print()
    print('========================================================')
    if ret == 0:
        print('【大功告成！】')
        print('可执行文件已生成在: dist\\OmniFinder.exe')
        print('您可以直接将 dist\\OmniFinder.exe 复制给任何人使用！')
    else:
        print('打包遇到错误，请查看上方提示信息。')
    print('========================================================')
    input('按回车键退出...')

if __name__ == '__main__':
    main()
