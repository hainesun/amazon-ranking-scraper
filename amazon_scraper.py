import os
import time
import random
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

# 保存設定
SAVE_DIR = "."
TARGET_URL = "https://www.amazon.co.jp/gp/bestsellers/kitchen/"
USER_DATA_DIR = "./my_browser_data"

def save_image(url, path):
    try:
        if not url: return False
        # URLの「._AC_...」などのリサイズ指定を削除して、本来の高画質URLにする
        high_res_url = url.split("._")[0] + ".jpg"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Referer": "https://www.amazon.co.jp/"
        }
        res = requests.get(high_res_url, headers=headers, timeout=10)
        if res.status_code == 200:
            with open(path, 'wb') as f:
                f.write(res.content)
            return True
    except:
        pass
    return False

def generate_html(results):
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    # ★ここからデザイン変更：テーブル（リスト）形式にするCSS
    html = f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Amazon LP Archive</title>
    <style>
        body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f9f9f9;padding:20px;color:#333}}
        h1{{text-align:center;margin-bottom:20px;color:#232f3e}}
        /* テーブルのデザイン */
        table {{width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1);}}
        th, td {{border: 1px solid #ddd; padding: 15px; vertical-align: top;}}
        th {{background: #232f3e; color: white; text-align: left;}}
        
        /* 各列の幅調整 */
        .col-rank {{width: 60px; text-align: center; font-weight: bold; font-size: 1.5em; color: #e47911;}}
        .col-main {{width: 150px; text-align: center;}}
        .col-info {{width: 25%;}}
        .col-lp {{}} /* 残りの幅全部 */

        /* 画像のデザイン */
        .main-img {{width: 120px; border: 1px solid #eee;}}
        .lp-gallery {{display: flex; gap: 10px; overflow-x: auto; padding-bottom: 10px;}}
        .lp-gallery img {{height: 120px; border: 1px solid #ccc; border-radius: 4px; transition: transform 0.2s;}}
        .lp-gallery img:hover {{transform: scale(1.1); border-color: #e47911;}}
        
        a {{text-decoration: none; color: #007185; font-weight: bold;}}
        a:hover {{text-decoration: underline; color: #c7511f;}}
    </style></head><body>
    <h1>Amazon LP Archive ({now_str})</h1>
    <table>
        <thead>
            <tr>
                <th>順位</th>
                <th>メイン画像</th>
                <th>商品情報</th>
                <th>LP・サブ画像構成 (横スクロール)</th>
            </tr>
        </thead>
        <tbody>
    """
    
    for r in results:
        subs_html = "".join([f'<a href="{s}" target="_blank"><img src="{s}"></a>' for s in r["subs"]])
        html += f"""
        <tr>
            <td class="col-rank">{r["rank"]}</td>
            <td class="col-main">
                <a href="{r['main']}" target="_blank"><img src="{r['main']}" class="main-img"></a>
            </td>
            <td class="col-info">
                <a href="{r['url']}" target="_blank">{r['title']}</a>
                <br><br>
                <small style="color:#666">クリックで商品ページへ</small>
            </td>
            <td class="col-lp">
                <div class="lp-gallery">
                    {subs_html if subs_html else "<span style='color:#999'>サブ画像なし</span>"}
                </div>
            </td>
        </tr>
        """
    html += "</tbody></table></body></html>"
    with open(os.path.join(SAVE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

def run_scraper():
    if not os.path.exists(SAVE_DIR): os.makedirs(SAVE_DIR)
    
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            channel="chrome",
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = browser.pages[0]
        
        print("Amazonにアクセスします...")
        try:
            page.goto(TARGET_URL, wait_until="domcontentloaded")
        except:
            print("読み込み継続中...")

        print("\n" + "="*50)
        print("【確認】")
        print("1. ロボット確認が出たら手動でクリア")
        print("2. ランキングが表示されたら、この画面でエンターキーを押す")
        print("="*50 + "\n")
        input("準備OKならエンターキーを押す >> ")

        # 商品リスト取得
        selectors = [".p13n-sc-unpb-faceout", "#gridItemRoot", ".zg-grid-general-faceout", "div[id^='p13n-asin-index']"]
        items = []
        for sel in selectors:
            found = page.query_selector_all(sel)
            if len(found) > 0:
                items = found[:10]
                break
        
        print(f"{len(items)}件の商品を処理します。")
        results = []

        for i, item in enumerate(items):
            rank = i + 1
            print(f"処理中: {rank}位...")
            
            # リンク取得
            link = item.query_selector("a.a-link-normal")
            if not link: link = item.query_selector("a")
            if not link: continue

            url_part = link.get_attribute("href")
            url = "https://www.amazon.co.jp" + url_part if not url_part.startswith("http") else url_part
            
            # タイトル
            title_el = item.query_selector(".p13n-sc-truncate-desktop-type2")
            if not title_el: title_el = item.query_selector("div[class*='truncate']")
            title_text = title_el.inner_text().strip() if title_el else f"Item {rank}"
            
            # メイン画像
            main_img = f"rank{rank:02d}_main.jpg"
            img_el = item.query_selector("img")
            if img_el: save_image(img_el.get_attribute("src"), main_img)
            
            # 詳細ページでサブ画像を「裏技」で取得（上位3件）
            subs = []
            if rank <= 3: 
                try:
                    p2 = browser.new_page()
                    p2.goto(url, wait_until="domcontentloaded")
                    time.sleep(2)
                    
                    # ホバーせず、サムネイルのURLから直接高画質版を取得
                    thumb_imgs = p2.query_selector_all("#altImages li.item.imageThumbnail img")
                    for j, img in enumerate(thumb_imgs[1:7]):
                        src = img.get_attribute("src")
                        if src:
                            s_name = f"rank{rank:02d}_{j+2:02d}.jpg"
                            if save_image(src, s_name):
                                subs.append(s_name)
                    p2.close()
                except Exception as e:
                    print(f"詳細エラー: {e}")
                    if not p2.is_closed(): p2.close()

            results.append({"rank": rank, "title": title_text, "url": url, "main": main_img, "subs": subs})
            time.sleep(1)

        generate_html(results)
        print("\n🎉 完了！ git push してください。")
        browser.close()

if __name__ == "__main__":
    run_scraper()