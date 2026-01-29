import os
import requests
from playwright.sync_api import sync_playwright
from datetime import datetime

SAVE_DIR = "public" # GitHub Pages用にフォルダ名をpublicに変更
TARGET_URL = "https://www.amazon.co.jp/gp/bestsellers/kitchen/"

def save_image(url, path):
    try:
        high_res_url = url.split("._")[0] + ".jpg"
        res = requests.get(high_res_url, timeout=15)
        if res.status_code == 200:
            with open(path, 'wb') as f:
                f.write(res.content)
            return True
    except:
        pass
    return False

def run_scraper():
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            locale="ja-JP"
        )
        page = context.new_page()
        page.set_default_timeout(60000)
        
        print("Amazonランキング取得開始...")
        page.goto(TARGET_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

        items = page.query_selector_all(".p13n-sc-unpb-faceout")[:10]
        results = []

        for i, item in enumerate(items):
            rank = i + 1
            link_el = item.query_selector("a")
            if not link_el: continue
            
            title = f"Product {rank}"
            title_el = item.query_selector(".p13n-sc-truncate-desktop-type2")
            if title_el: title = title_el.inner_text().strip()
            
            url = "https://www.amazon.co.jp" + link_el.get_attribute("href")
            main_img_name = f"rank{rank}_main.jpg"
            img_el = item.query_selector("img")
            
            if img_el:
                save_image(img_el.get_attribute("src"), os.path.join(SAVE_DIR, main_img_name))

            sub_images = []
            reviews = ""
            if rank <= 5: # 上位5件のみ詳細解析
                print(f"詳細解析中: {rank}位")
                det_page = context.new_page()
                det_page.goto(url, wait_until="domcontentloaded")
                det_page.wait_for_timeout(3000)
                
                thumbs = det_page.query_selector_all("#altImages .a-spacing-smallitem")
                for j, thumb in enumerate(thumbs[:6]):
                    thumb.hover()
                    det_page.wait_for_timeout(700)
                    large = det_page.query_selector("#landingImage")
                    if large:
                        img_name = f"rank{rank}_sub{j}.jpg"
                        if save_image(large.get_attribute("src"), os.path.join(SAVE_DIR, img_name)):
                            sub_images.append(img_name)
                
                rev_els = det_page.query_selector_all(".review-text-content span")
                reviews = "<br>".join([r.inner_text() for r in rev_els[:2]])
                det_page.close()

            results.append({"rank": rank, "title": title, "main": main_img_name, "subs": sub_images, "reviews": reviews})

        # --- HTML生成 ---
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        html = f"""
        <html><head><meta charset="utf-8"><title>Amazon LP Archive</title>
        <style>
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background: #f0f2f2; margin: 0; padding: 20px; }}
            .container {{ max-width: 1000px; margin: auto; }}
            .card {{ background: white; margin-bottom: 30px; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #232f3e; text-align: center; }}
            .rank {{ font-size: 24px; font-weight: bold; color: #e47911; }}
            .img-row {{ display: flex; overflow-x: auto; gap: 10px; margin: 15px 0; }}
            .img-row img {{ height: 200px; border: 1px solid #ddd; border-radius: 5px; }}
            .reviews {{ font-size: 0.9em; color: #555; background: #f9f9f9; padding: 10px; border-radius: 5px; }}
        </style></head>
        <body><div class="container">
            <h1>Amazon Daily LP Archive ({now_str})</h1>
        """
        for r in results:
            html += f"""
            <div class="card">
                <div class="rank">第{r['rank']}位</div>
                <div class="title">{r['title']}</div>
                <div class="img-row">
                    <img src="{r['main']}">
                    {' '.join([f'<img src="{s}">' for s in r['subs']])}
                </div>
                <div class="reviews"><b>主なレビュー:</b><br>{r['reviews']}</div>
            </div>
            """
        html += "</div></body></html>"
        with open(os.path.join(SAVE_DIR, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)

        browser.close()

if __name__ == "__main__":
    run_scraper()