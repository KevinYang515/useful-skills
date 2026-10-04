# useful-skills

我自己整理的 [Claude Code skills](https://docs.claude.com/en/docs/claude-code)，每個資料夾是一個獨立的 skill（跟 Claude Code 讀 `~/.claude/skills/<名稱>/SKILL.md` 的方式一致），可以單獨複製使用，不互相依賴。

## 目前有的 skill

- **[threads-scraper](threads-scraper/SKILL.md)**：擷取 Threads 貼文的內容、留言、圖片影片，並對圖片做 OCR（辨識截圖/對帳單裡的文字）。可用。
- **facebook-scraper**：同樣功能的 Facebook 版本，還在開發中，細節見 [facebook-scraper/NOTE.md](facebook-scraper/NOTE.md)。

## 怎麼用（給朋友）

```bash
git clone <這個repo的網址> useful-skills
```

**方法一：整個資料夾當作你的 skills 目錄**（如果你還沒有自己的 `~/.claude/skills/`）
```bash
# Windows，~ 通常是 C:\Users\你的帳號
cp -r useful-skills/* ~/.claude/skills/
```

**方法二：只拿某一個 skill**（如果你已經有別的 skills 了）
```bash
cp -r useful-skills/threads-scraper ~/.claude/skills/threads-scraper
```

兩種都好之後跑：
```bash
cd ~/.claude/skills/threads-scraper   # 或你複製過去的位置
pip install -r requirements.txt
python threads_scrape.py --login      # 第一次用要先登入一次
```

之後在 Claude Code 裡直接說「幫我抓這篇 threads 貼文 <網址>」就會自動觸發這個 skill。不用 Claude Code 也可以，直接當一般 Python 腳本跑：`python threads_scrape.py "<貼文網址>"`。

## 安裝需求

- Windows + 系統已裝 Microsoft Edge（Windows 11 內建就有）。用的是系統原生 Edge（`playwright` 的 `channel="msedge"`），不用另外下載瀏覽器核心，省掉 Playwright 預設會抓的那包 Chromium。
- Python 3.10+，`pip install -r requirements.txt`（`playwright`、`requests`、`rapidocr-onnxruntime`）。

## 注意事項

僅供個人研究/備份使用，請遵守 Threads / Facebook 的服務條款，不要大量高頻爬取或散布他人未公開內容。每個 skill 資料夾裡的 `profile/`（瀏覽器登入憑證）已被 `.gitignore` 排除，不會被推上 GitHub——每個人要用自己的帳號登入一次，不能共用別人的登入狀態。
