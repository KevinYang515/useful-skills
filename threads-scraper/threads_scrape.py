"""Threads 貼文擷取工具：文章內容、留言、圖片。

用法:
  python threads_scrape.py <threads貼文網址> [--out 輸出資料夾] [--scrolls 15] [--headed] [--login]
  --login  開啟有畫面的瀏覽器讓你手動登入一次，登入狀態存在 profile 資料夾，之後重複使用。
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ocr_util import ocr_image  # noqa: E402

BASE = Path(__file__).parent
PROFILE = BASE / "profile"
VERBOSE = "--verbose" in sys.argv


def best_image(node):
    cands = (node.get("image_versions2") or {}).get("candidates") or []
    if not cands:
        return None
    return max(cands, key=lambda c: c.get("width", 0) * c.get("height", 0)).get("url")


def media_of(node):
    """回傳 [{'type','url'}]，含輪播圖與影片。"""
    out = []
    carousel = node.get("carousel_media")
    items = carousel if carousel else [node]
    for it in items:
        vids = it.get("video_versions") or []
        if vids:
            out.append({"type": "video", "url": vids[0].get("url")})
        img = best_image(it)
        if img:
            out.append({"type": "video_cover" if vids else "image", "url": img})
    return out


def to_post(node):
    user = node.get("user") or {}
    caption = node.get("caption") or {}
    info = node.get("text_post_app_info") or {}
    ts = node.get("taken_at")
    return {
        "id": str(node.get("pk") or node.get("id")),
        "code": node.get("code"),
        "author": user.get("username"),
        "text": caption.get("text") or "",
        "time": datetime.fromtimestamp(ts, timezone.utc).isoformat() if ts else None,
        "likes": node.get("like_count"),
        "replies_count": info.get("direct_reply_count"),
        "reply_to": (info.get("reply_to_author") or {}).get("username"),
        "media": media_of(node),
    }


def merge_raw(old, new):
    """同一則貼文常在頁面內出現多份節點（例如 /media 燈箱路由會同時塞一份完整版和一份缺 caption 的精簡版）。
    採欄位級合併、保留先出現的非空值，避免後來的精簡版把已抓到的內容蓋成空的。"""
    if old is None:
        return dict(new)
    merged = dict(old)
    for k, v in new.items():
        if v in (None, "", [], {}):
            continue
        if merged.get(k) in (None, "", [], {}):
            merged[k] = v
    return merged


def walk(obj, raw):
    if isinstance(obj, dict):
        if obj.get("pk") and obj.get("code") and "user" in obj and ("caption" in obj or "text_post_app_info" in obj):
            key = str(obj["pk"])
            raw[key] = merge_raw(raw.get(key), obj)
        for v in obj.values():
            walk(v, raw)
    elif isinstance(obj, list):
        for v in obj:
            walk(v, raw)


def try_json(text):
    try:
        return json.loads(text)
    except Exception:
        return None


def scrape(url, scrolls, headed):
    raw = {}
    PROFILE.mkdir(exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), channel="msedge", headless=not headed,
            locale="zh-TW", viewport={"width": 1200, "height": 1000},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        def on_response(resp):
            if "graphql" not in resp.url and "/api/" not in resp.url:
                return
            try:
                data = try_json(resp.text())
            except Exception:
                return
            if data:
                walk(data, raw)

        page.on("response", on_response)
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)

        # 頁面內嵌的初始資料
        for s in page.query_selector_all('script[type="application/json"]'):
            d = try_json(s.inner_text())
            if d:
                walk(d, raw)

        stable = 0
        last = -1
        for _ in range(scrolls):
            page.mouse.move(600, 600)
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(1800)
            if VERBOSE:
                replies = sum(1 for v in raw.values() if (v.get("text_post_app_info") or {}).get("reply_to_author"))
                print("scroll: posts", len(raw), "replies", replies, file=sys.stderr)
            stable = stable + 1 if len(raw) == last else 0
            last = len(raw)
            if stable >= 6:
                break

        # 展開收合的巢狀回覆（「顯示回覆」按鈕，跟會打斷捲動載入的「查看更多/View more」分頁按鈕不同，這個只是單純展開，可以安全點擊）
        for _ in range(10):
            buttons = page.query_selector_all(
                'div[role="button"]:has-text("顯示回覆"), div[role="button"]:has-text("Show replies")'
            )
            if not buttons:
                break
            clicked = 0
            for b in buttons:
                try:
                    b.click(timeout=1500)
                    clicked += 1
                    page.wait_for_timeout(1200)
                except Exception:
                    pass
            if VERBOSE:
                print("展開巢狀回覆:", clicked, "個按鈕, posts", len(raw), file=sys.stderr)
            if clicked == 0:
                break
            page.wait_for_timeout(1000)

        ctx.close()
    return {k: to_post(v) for k, v in raw.items()}


def login():
    PROFILE.mkdir(exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(PROFILE), channel="msedge", headless=False, locale="zh-TW")
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://www.threads.com/login")
        print("請在 Edge 視窗登入 Threads，完成後直接關閉該視窗即可。", flush=True)
        try:
            ctx.wait_for_event("close", timeout=0)
        except Exception:
            pass


def download(media, folder, prefix, do_ocr=True):
    folder.mkdir(parents=True, exist_ok=True)
    for i, m in enumerate(media, 1):
        ext = "mp4" if m["type"] == "video" else (Path(urlparse(m["url"]).path).suffix.lstrip(".") or "jpg")
        path = folder / f"{prefix}_{i}.{ext}"
        try:
            r = requests.get(m["url"], timeout=60)
            r.raise_for_status()
            path.write_bytes(r.content)
            m["file"] = str(path.relative_to(folder.parent))
            if do_ocr and m["type"] in ("image", "video_cover"):
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
    ap.add_argument("--scrolls", type=int, default=100)
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--login", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--no-media", action="store_true")
    ap.add_argument("--no-ocr", action="store_true", help="下載圖片但不辨識圖片裡的文字")
    a = ap.parse_args()

    if a.login:
        return login()
    if not a.url:
        ap.error("請提供貼文網址")

    m = re.search(r"/post/([\w-]+)", a.url)
    main_code = m.group(1) if m else None
    found = scrape(a.url, a.scrolls, a.headed)
    if not found:
        sys.exit("沒有抓到任何內容（可能需要登入：先執行 --login，或網址錯誤）")

    posts = sorted(found.values(), key=lambda x: x["time"] or "")
    main_post = next((x for x in posts if x["code"] == main_code), posts[0])
    comments = [x for x in posts if x["id"] != main_post["id"] and x["reply_to"]]

    out = Path(a.out) / (main_code or main_post["id"])
    if not a.no_media:
        do_ocr = not a.no_ocr
        download(main_post["media"], out / "images", "post", do_ocr)
        for c in comments:
            if c["media"]:
                download(c["media"], out / "images", f"comment_{c['id']}", do_ocr)

    result = {"url": a.url, "post": main_post, "comments": comments}
    out.mkdir(parents=True, exist_ok=True)
    (out / "data.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    def media_lines(items):
        lines = []
        for x in items:
            lines.append(f"- {x['type']}: {x.get('file') or x['url']}")
            if x.get("ocr_text"):
                quoted = "\n".join(f"  > {line}" for line in x["ocr_text"].splitlines())
                lines.append(f"  （圖片文字 OCR）\n{quoted}")
        return lines

    md = [f"# @{main_post['author']}  {main_post['time']}\n", main_post["text"], ""]
    md += media_lines(main_post["media"])
    md.append(f"\n讚 {main_post['likes']}｜留言 {main_post['replies_count']}\n\n## 留言 ({len(comments)})\n")
    for c in comments:
        md.append(f"**@{c['author']}** ({c['time']}, 讚 {c['likes']})\n\n{c['text']}\n")
        md += media_lines(c["media"])
        md.append("")
    (out / "post.md").write_text("\n".join(md), encoding="utf-8")
    total = main_post["replies_count"] or 0
    if total and len(comments) < total * 0.9:
        print(f"注意：貼文顯示 {total} 則留言，只取得 {len(comments)} 則。可能是尚未登入（先執行 --login）、被隱藏/刪除的留言，或收合的巢狀回覆未展開。", file=sys.stderr)
    print(f"完成：主文 1 篇、留言 {len(comments)} 則 -> {out}")


if __name__ == "__main__":
    main()
