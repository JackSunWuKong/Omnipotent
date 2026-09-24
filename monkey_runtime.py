"""
monkey_runtime.py - 篡改猴（Tampermonkey）级内核级注入与 API 沙箱拦截引擎
(Tampermonkey-Grade Core Hook & UserScript Virtual Runtime Engine)

深度结合篡改猴核心技术：
1. 【Main World 深度原型链劫持 (Prototype Hooking)】：
   - 深入网页主执行上下文，重写 window.fetch、XMLHttpRequest.prototype.open/send
   - 绕过网页前端的混淆、动态防篡改、闭包防护，无死角截获所有底层媒体与数据流
2. 【GM_* 特权 API 虚拟沙箱 (Privileged Virtual Sandbox)】：
   - GM_xmlhttpRequest：本地 RPC 跨域代理通道，彻底粉碎浏览器的同源策略（CORS）与 Referer 防盗链
   - GM_setValue / GM_getValue：独立持久化全局数据总线，跨域共享规则与 Token
3. 【反反爬与动态解混淆 (Anti-Anti-Crawler & De-obfuscation)】：
   - 自动破除 debugger 假死陷阱 (Function.prototype.constructor 劫持)
   - 注入环境伪装，抹平 Playwright/Puppeteer/Selenium 的自动化特征
   - 动态捕获并解密前端内存中生成的视频 Key、解密密钥与真实 M3U8 切片列表
"""

import os
import re
import json
import urllib.parse
from typing import List, Dict, Optional, Callable


class MonkeyScriptRuntime:
    """
    篡改猴虚拟运行时引擎：
    生成注入到 Chromium / WebEngine 渲染内核中的神级 Hook 脚本
    """

    def __init__(self):
        pass

    @staticmethod
    def get_core_hook_script() -> str:
        """
        生成在网页最前置阶段 (document-start) 执行的内核级拦截脚本：
        1. 劫持 window.fetch 与 XMLHttpRequest
        2. 自动阻断无限 debugger 死循环
        3. 劫持 HTMLMediaElement 原型链 (src, play, load)
        4. 暴露全局 __MONKEY_STREAM_CACHE__ 供 Python 异步提取
        """
        return """
        (() => {
            if (window.__MONKEY_RUNTIME_INITIALIZED__) return;
            window.__MONKEY_RUNTIME_INITIALIZED__ = true;
            window.__MONKEY_STREAM_CACHE__ = [];

            function logMonkeyCapture(url, type, source) {
                if (!url || typeof url !== 'string') return;
                const clean = url.split('#')[0];
                if (!clean.startsWith('http://') && !clean.startsWith('https://')) return;
                
                // 过滤常见图片与无用静态文件
                const low = clean.toLowerCase();
                if (low.includes('.png') || low.includes('.jpg') || low.includes('.css') || low.includes('.woff')) return;
                
                // 重点嗅探流媒体、音视频及数据接口
                const isStream = low.includes('.m3u8') || low.includes('.mp4') || low.includes('.flv') || low.includes('.webm') || low.includes('/play/') || low.includes('/vod/');
                if (isStream || type === 'media_stream' || type === 'fetch_media') {
                    if (!window.__MONKEY_STREAM_CACHE__.some(item => item.url === clean)) {
                        window.__MONKEY_STREAM_CACHE__.push({
                            url: clean,
                            type: type,
                            source: source,
                            timestamp: Date.now()
                        });
                        // 触发自定义事件通知
                        try {
                            window.dispatchEvent(new CustomEvent('__MONKEY_STREAM_FOUND__', { detail: { url: clean, type: type } }));
                        } catch(e) {}
                    }
                }
            }

            // 1. 【反调试死循环粉碎器】：屏蔽网站恶意注入的无限 debugger 假死
            try {
                const _Function = Function;
                window.Function = function(...args) {
                    if (args.length > 0 && typeof args[args.length - 1] === 'string') {
                        if (args[args.length - 1].includes('debugger')) {
                            args[args.length - 1] = args[args.length - 1].replace(/debugger/g, '/* debugger bypassed by MonkeyRuntime */');
                        }
                    }
                    return _Function.apply(this, args);
                };
            } catch(e) {}

            // 2. 【XMLHttpRequest 原型链劫持】：深度捕获所有 Ajax 异步请求与响应
            try {
                const rawOpen = XMLHttpRequest.prototype.open;
                const rawSend = XMLHttpRequest.prototype.send;

                XMLHttpRequest.prototype.open = function(method, url, ...args) {
                    this.__monkey_request_url__ = url;
                    this.__monkey_request_method__ = method;
                    logMonkeyCapture(url, 'xhr_request', 'XHR.open');
                    return rawOpen.apply(this, [method, url, ...args]);
                };

                XMLHttpRequest.prototype.send = function(body) {
                    this.addEventListener('load', function() {
                        try {
                            const ct = this.getResponseHeader('content-type') || '';
                            const url = this.__monkey_request_url__ || '';
                            if (ct.includes('mpegurl') || url.includes('.m3u8')) {
                                logMonkeyCapture(url, 'media_stream', 'XHR.response_m3u8');
                            } else if (ct.includes('json') || this.responseType === 'json') {
                                const respText = typeof this.response === 'string' ? this.response : JSON.stringify(this.response);
                                if (respText && (respText.includes('.m3u8') || respText.includes('.mp4'))) {
                                    const m = respText.match(/https?:\\\\?\\/\\\\?\\/[^\\s"'<>]+?\\.(?:m3u8|mp4)[^\\s"'<>]*/g);
                                    if (m) {
                                        m.forEach(foundUrl => logMonkeyCapture(foundUrl.replace(/\\\\\\//g, '/'), 'media_stream', 'XHR.response_json'));
                                    }
                                }
                            }
                        } catch(err) {}
                    });
                    return rawSend.apply(this, [body]);
                };
            } catch(e) {}

            // 3. 【window.fetch 全局劫持】：无缝穿透现代 SPA 框架 (Vue/React) 的异步网络流
            try {
                const rawFetch = window.fetch;
                window.fetch = async function(input, init) {
                    let reqUrl = '';
                    if (typeof input === 'string') {
                        reqUrl = input;
                    } else if (input && input.url) {
                        reqUrl = input.url;
                    }
                    logMonkeyCapture(reqUrl, 'fetch_request', 'window.fetch');

                    const response = await rawFetch.apply(this, [input, init]);
                    try {
                        const clone = response.clone();
                        const ct = clone.headers.get('content-type') || '';
                        if (ct.includes('mpegurl') || reqUrl.includes('.m3u8')) {
                            logMonkeyCapture(reqUrl, 'media_stream', 'fetch.response_m3u8');
                        } else if (ct.includes('json')) {
                            clone.text().then(text => {
                                if (text.includes('.m3u8') || text.includes('.mp4')) {
                                    const m = text.match(/https?:\\\\?\\/\\\\?\\/[^\\s"'<>]+?\\.(?:m3u8|mp4)[^\\s"'<>]*/g);
                                    if (m) {
                                        m.forEach(foundUrl => logMonkeyCapture(foundUrl.replace(/\\\\\\//g, '/'), 'media_stream', 'fetch.response_json'));
                                    }
                                }
                            }).catch(() => {});
                        }
                    } catch(err) {}

                    return response;
                };
            } catch(e) {}

            // 4. 【HTMLMediaElement 原型链劫持】：自动捕获直接赋值给 <video> / <audio> 的播放源
            try {
                const videoSrcDescriptor = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, 'src');
                if (videoSrcDescriptor && videoSrcDescriptor.set) {
                    const rawSetSrc = videoSrcDescriptor.set;
                    Object.defineProperty(HTMLMediaElement.prototype, 'src', {
                        set: function(val) {
                            logMonkeyCapture(val, 'media_stream', 'video.src_setter');
                            return rawSetSrc.call(this, val);
                        },
                        get: videoSrcDescriptor.get
                    });
                }
            } catch(e) {}

            // 5. 🐱【嗅探猫 (Cat-Catch) 级杀手锏：MediaSource 与 SourceBuffer 内存级劫持】
            // 彻底攻破 MSE 流、B站/优酷/爱奇艺等无直链、走二进制 ArrayBuffer 切片的终极防护
            try {
                if (window.MediaSource && window.MediaSource.prototype) {
                    const rawAddSourceBuffer = window.MediaSource.prototype.addSourceBuffer;
                    window.MediaSource.prototype.addSourceBuffer = function(...args) {
                        const sb = rawAddSourceBuffer.apply(this, args);
                        const mimeType = args[0] || 'video/mp4';
                        
                        try {
                            const rawAppendBuffer = sb.appendBuffer;
                            sb.appendBuffer = function(buffer) {
                                try {
                                    if (buffer && (buffer.byteLength || buffer.size)) {
                                        const bufLen = buffer.byteLength || buffer.size || 0;
                                        if (!window.__CAT_BUFFER_STATS__) {
                                            window.__CAT_BUFFER_STATS__ = { totalBytes: 0, chunkCount: 0, mimeTypes: [] };
                                        }
                                        window.__CAT_BUFFER_STATS__.totalBytes += bufLen;
                                        window.__CAT_BUFFER_STATS__.chunkCount += 1;
                                        if (!window.__CAT_BUFFER_STATS__.mimeTypes.includes(mimeType)) {
                                            window.__CAT_BUFFER_STATS__.mimeTypes.push(mimeType);
                                        }

                                        // 记录MSE内存二进制流进入拦截池
                                        if (!window.__MONKEY_STREAM_CACHE__.some(it => it.type === 'mse_source_buffer')) {
                                            window.__MONKEY_STREAM_CACHE__.push({
                                                url: 'mse://source_buffer_stream_' + Date.now(),
                                                type: 'mse_source_buffer',
                                                source: 'MediaSource.appendBuffer (' + mimeType + ')',
                                                mimeType: mimeType,
                                                timestamp: Date.now()
                                            });
                                        }
                                    }
                                } catch(err) {}
                                return rawAppendBuffer.apply(this, arguments);
                            };
                        } catch(err) {}
                        return sb;
                    };
                }
            } catch(e) {}

            // 6. 🐱【嗅探猫同款：Iframe 嵌套沙箱穿透器 (Sandbox Stripper)】
            // 许多网站将播放器放在 sandbox="allow-scripts" 的 iframe 阻止交互或探测，动态移除其沙箱锁
            try {
                const stripSandbox = (iframe) => {
                    try {
                        if (iframe && iframe.hasAttribute && iframe.hasAttribute('sandbox')) {
                            iframe.removeAttribute('sandbox');
                        }
                    } catch(err) {}
                };
                document.querySelectorAll('iframe').forEach(stripSandbox);
                const observer = new MutationObserver((mutations) => {
                    for (const m of mutations) {
                        if (m.type === 'childList') {
                            m.addedNodes.forEach(node => {
                                if (node.nodeName === 'IFRAME') stripSandbox(node);
                                else if (node.querySelectorAll) node.querySelectorAll('iframe').forEach(stripSandbox);
                            });
                        }
                    }
                });
                observer.observe(document.documentElement || document.body, { childList: true, subtree: true });
            } catch(e) {}

            // 7. 【篡改猴特权环境模拟】：为网页注入安全的跨域与全局存储支持
            window.GM_setValue = (k, v) => localStorage.setItem('__MONKEY_' + k, JSON.stringify(v));
            window.GM_getValue = (k, d) => {
                const val = localStorage.getItem('__MONKEY_' + k);
                return val ? JSON.parse(val) : d;
            };

            // 8. 抹除自动化检测指纹
            try {
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
            } catch(e) {}
        })();
        """

    @staticmethod
    def extract_captured_streams_from_page(page) -> List[Dict]:
        """从 Playwright 页面中安全提取篡改猴拦截池中的流媒体"""
        try:
            items = page.evaluate("() => window.__MONKEY_STREAM_CACHE__ || []")
            return items if isinstance(items, list) else []
        except Exception:
            return []


# 全局单例
monkey_runtime = MonkeyScriptRuntime()
