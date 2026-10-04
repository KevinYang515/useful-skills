---
name: threads-scraper
description: "Scrape a Threads (threads.com / threads.net) post's text, comments/replies, and images/videos into local files. MANDATORY TRIGGERS: '抓threads', '爬threads', 'threads貼文', 'threads留言', 'scrape threads post'. STRONG TRIGGERS: 使用者貼一個 threads.com/@.../post/... 網址並要求擷取內容、留言或圖片。Do NOT trigger for Twitter/X, Instagram feed browsing, or general web scraping unrelated to Threads."
---

# Threads 貼文擷取工具

工具就在這個 skill 自己的資料夾裡：`threads_scrape.py`（跟這份 SKILL.md 同一層。Claude 載入這份 skill 時系統會告訴你「Base directory for this skill」，用那個完整路徑組出指令，例如 `python <base>\threads_scrape.py ...`）。

需求：Windows + 系統已裝 Microsoft Edge（Windows 11 內建就有，不需要另外下載瀏覽器）。第一次使用前要跑過 repo 根目錄 `requirements.txt` 的安裝（`pip install -r requirements.txt`：`playwright`、`requests`、`rapidocr-onnxruntime`）。

## 用法

```
python threads_scrape.py "https://www.threads.com/@帳號/post/貼文代碼"
```

常用參數：
- `--no-media`：不下載圖片/影片，只要文字資料時加快速度。
- `--no-ocr`：圖片照樣下載，但不辨識圖片裡的文字（OCR 較慢時可跳過）。
- `--verbose`：印出捲動進度（除錯用）。
- `--scrolls N`：最多捲動幾次，預設 100（留言少的貼文會提早自動停止）。
- `--headed`：顯示瀏覽器視窗（除錯用，預設無頭執行）。

## 輸出

`output\<貼文代碼>\` 底下：
- `post.md`：主文 + 全部留言的可讀版本，圖片下面會附「（圖片文字 OCR）」區塊，是辨識出圖片裡「畫」出來的文字（截圖、對帳單、標語牌之類），不是貼文本身的 caption。
- `data.json`：結構化資料（作者、時間、讚數、留言的 `reply_to`、每個媒體項目的 `ocr_text`）。
- `images\`：主文與留言的圖片/影片，影片會附一張封面圖（封面圖也會做 OCR，影片本身不會）。

## OCR（圖片內文字辨識）

用 [RapidOCR](https://github.com/RapidAI/RapidOCR)（`rapidocr-onnxruntime`，純 pip 安裝、不需另外裝執行檔、CPU 可跑）。`ocr_util.py` 就放在這個 skill 資料夾裡（跟 `facebook-scraper` skill 各自一份，故意不共用路徑，保持每個 skill 資料夾能單獨複製搬動）。辨識中英文皆可，但模型偏簡體中文訓練，遇到繁體或風格化字體（例如照片裡角度傾斜的招牌字）準確率會下降，這是預期限制，不是 bug——重要的圖片文字建議肉眼再核對一次 `images\` 資料夾裡的原圖。

## 登入（拿到完整留言必須做，且只需做一次）

Threads 未登入狀態下留言只會載入一小部分（實測一篇 382 則留言的貼文，未登入只拿到 14~18 則，登入後可拿到 326+ 則，仍可能因隱藏/刪除留言而略少於總數，屬正常現象）。

```
python threads_scrape.py --login
```

會開一個有畫面的 Edge 視窗，手動登入 Threads 帳號後**直接關閉該視窗**（不要用 Enter，有些環境的 stdin 是關閉的，`input()` 會直接丟 EOFError）。登入狀態存在這個資料夾底下的 `profile\`（含個人登入憑證，已被 `.gitignore` 排除，不會被推上 GitHub，也不會被另一個人的 git pull 覆蓋掉），之後所有呼叫都會自動沿用，不用重複登入。

## 已知限制 / 踩過的坑

- **不要用「查看更多/View more」按鈕點擊來展開留言分頁**——實測點擊反而會打斷 Threads 的無限捲動載入，讓抓到的留言數量變少甚至卡住。現在的做法是純滑鼠滾輪捲動（`page.mouse.wheel`），效果最穩定。
- **「顯示回覆/Show replies」按鈕不一樣，要點**——這是收合的巢狀回覆（某則留言底下的子回覆）展開鈕，跟上面會打斷捲動的分頁按鈕是兩回事，點擊是安全的。程式在捲動結束後會自動找這個按鈕點開（最多重複 10 輪，直到沒有新按鈕為止）。若改動捲動邏輯時要注意別把這兩種按鈕搞混。
- **不要用 `document.scrollingElement.scrollHeight` 或 JS 硬設 `scrollTop`/`window.scrollTo` 來捲動**——Threads 頁面本體不會捲動（外層高度固定），實際可捲動的是內部一個 overflow 容器，用 JS 直接跳到底部會讓懶載入偵測不到捲動事件而不觸發新的 GraphQL 請求。純滑鼠滾輪事件才會被頁面正確偵測到。
- **同一則貼文在頁面 JSON 裡可能出現多份重複節點，欄位多寡不一**——例如網址是 `/post/代碼/media`（附圖燈箱格式）時，內嵌 JSON 會同時有一份完整版（含 `caption`）和一份給燈箱用的精簡版（沒有 `caption`）。程式用 `merge_raw()` 做欄位級合併（保留先抓到的非空值），不能改回直接覆蓋（`found[id] = ...`），否則精簡版會把已抓到的內文洗空。
- 過濾規則：只保留 `text_post_app_info.reply_to_author` 有值的節點當留言，用來排除頁面上混入的「猜你喜歡」推薦貼文；巢狀回覆（回覆別人留言而非回覆原PO）也會被抓到，但目前是攤平成同一個清單（用 `data.json` 裡每則留言的 `reply_to` 欄位可自行重建樹狀關係），不是巢狀輸出。
- 即使登入且巢狀回覆都展開了，抓到的留言數仍可能略少於貼文顯示的總數（例如顯示 11 則實際抓到 10 則）——通常是被刪除/隱藏的留言，非程式錯誤，數量差 1~2 成以內屬正常。
- 若某則留言的圖被抓到 `error` 欄位，代表下載失敗（連結過期或需要額外授權），文字內容不受影響。
