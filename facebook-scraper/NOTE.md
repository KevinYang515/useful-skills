# facebook-scraper（尚未完成，還沒有 SKILL.md）

`facebook_scrape.py` 目前只有登入流程，貼文/留言/圖片的擷取邏輯還沒寫完。

探索到的狀況：
- Facebook **未登入**時貼文連結、圖片、留言的 DOM 結構會被拿掉、全部導向登入頁，跟 Threads「未登入也能抓一部分」不一樣，這個工具必須先登入才有用。
- Facebook **登入後**貼文頁面（`www.facebook.com/<頁面>/posts/<id>`），貼文內文和前幾則留言其實是直接寫在 HTML 裡的純文字（不像 Threads 要去攔截 GraphQL），但還沒找到乾淨的 CSS selector 可以切出「每一則留言」的邊界（作者/內文/時間/讚數），需要用已登入的瀏覽器實測 DOM 結構才能把這段寫完。
- `mbasic.facebook.com`（早期輕量版）已經全面導向登入頁，不能用來繞過登入。

完成後會比照 `threads-scraper` 補上 `SKILL.md`。在那之前先不要靠這個 skill 的觸發詞叫 Claude 抓 Facebook 貼文，會失敗。
