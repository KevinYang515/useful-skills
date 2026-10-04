"""共用 OCR 工具：抓圖片裡「畫」出來的文字（截圖、對帳單等），不是貼文本身的 caption。
給 threads_scrape.py / facebook_scrape.py 共用，用 sys.path.insert(0, r"E:\\scraper_common") 後 import。
"""
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _engine = RapidOCR()
    return _engine


def ocr_image(path):
    """回傳圖片裡辨識到的文字（多行用換行接起來），辨識不到或出錯回傳空字串。"""
    try:
        result, _ = get_engine()(str(path))
    except Exception:
        return ""
    if not result:
        return ""
    return "\n".join(line[1] for line in result if line[1].strip())
