"""Facebook 貼文擷取工具：文章內容、留言、圖片（含 OCR）。

用法:
  python facebook_scrape.py <facebook貼文網址> [--out 輸出資料夾] [--headed] [--login]
  --login  開啟有畫面的瀏覽器讓你手動登入一次，登入狀態存在 profile 資料夾，之後重複使用。

前置需求：先執行 --login。Facebook 未登入時貼文連結、圖片、留言的 DOM 結構會被拿掉
（全部導向登入頁），跟 Threads 不一樣，這裡沒有「未登入部分可用」的退路。
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ocr_util import ocr_image  # noqa: E402

BASE = Path(__file__).parent
PROFILE = BASE / "profile"
VERBOSE = "--verbose" in sys.argv


def login():
    PROFILE.mkdir(exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(PROFILE), channel="msedge", headless=False, locale="zh-TW")
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://www.facebook.com/login")
        print("請在 Edge 視窗登入 Facebook，完成後直接關閉該視窗即可。", flush=True)
        try:
            ctx.wait_for_event("close", timeout=0)
        except Exception:
            pass


def download(media, folder, prefix, do_ocr=True):
    folder.mkdir(parents=True, exist_ok=True)
    for i, m in enumerate(media, 1):
        ext = "mp4" if m["type"] == "video" else (Path(urlparse(m["url"]).path).suffix.lstrip(".") or "jpg")
        ext = ext.split(";")[0][:4] or "jpg"
        path = folder / f"{prefix}_{i}.{ext}"
        try:
            r = requests.get(m["url"], timeout=60)
            r.raise_for_status()
            path.write_bytes(r.content)
            m["file"] = str(path.relative_to(folder.parent))
            if do_ocr and m["type"] == "image":
                text = ocr_image(path)
                if text:
                    m["ocr_text"] = text
        except Exception as e:
            m["error"] = str(e)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?")
    ap.add_argument("--out", default=str(BASE / "output"))
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--login", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--no-media", action="store_true")
    ap.add_argument("--no-ocr", action="store_true")
    a = ap.parse_args()

    if a.login:
        return login()
    if not a.url:
        ap.error("請提供貼文網址")

    if not PROFILE.exists():
        sys.exit("尚未登入，請先執行: python facebook_scrape.py --login")

    print("facebook_scrape.py 尚在開發中，DOM 結構要用真實登入狀態測過才能定案。", file=sys.stderr)


if __name__ == "__main__":
    main()
