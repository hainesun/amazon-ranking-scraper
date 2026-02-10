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
        # 例: image._AC_US40_.jpg -> image.jpg
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
    html = f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Amazon LP Archive</title><style>body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f4f4f4;padding:20px;color:#333}}.card{{background:white;margin-bottom:30px;padding:20px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.05)}}.rank-title{{font-weight:bold;font-size:1.2em;margin-bottom:15px;color:#e47911;display:flex;align-items:center;}}.main-img{{display:block;max-height:250px;margin:0 auto 20px;border:1px solid #eee}}.sub-gallery{{display:flex;overflow-x:auto;gap:10px;padding-bottom:10px}}.sub-gallery img{{height:180px;border-radius:6px;border:1px solid #ddd;transition:transform 0.2s}}.sub-gallery img:hover{{transform:scale(1.05)}}</style></head><body><h1>Amazon LP Archive ({now_str})</h1><div style="max-width:1000px;margin:auto;">"""
    
    for r in results:
        subs_html = "".join([f'<a href="{s}" target="_blank"><img src="{s}"></a>' for s in r["subs"]])
        html += f"""
        <div class="card">
            <div class="rank-title">👑 No.{r["rank"]} <a href="{r['url']}" target="_blank" style="margin-left:10px;text-decoration:none;color:#333">{r["title"]}</a></div>
            <div style="text-align:center"><small>メイン画像</small><br><img src="{r["main"]}" class="main-img"></div>
            <hr style="border:0;border-top:1px solid #eee;margin:20px 0">
            <strong>📸 LP・サブ画像</strong>
            <div class="sub-gallery">{subs_html if subs_html else "<span style='color:#999;font-size:0.9em'>サブ画像なし</span>"}</div>
        </div>
        """
    html += "</div></body></html>"
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
                    
                    # ★ここを変更：ホバーせず、サムネイルのURLから直接高画質版を取得
                    # 左側のサムネイル画像のリストを取得
                    thumb_imgs = p2.query_selector_all("#altImages li.item.imageThumbnail img")
                    
                    # 2枚目〜7枚目くらいを取得
                    for j, img in enumerate(thumb_imgs[1:7]):
                        src = img.get_attribute("src")
                        if src:
                            # ファイル名: rank01_02.jpg
                            s_name = f"rank{rank:02d}_{j+2:02d}.jpg"
                            # save_image関数内で自動的に高画質URLに変換される
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