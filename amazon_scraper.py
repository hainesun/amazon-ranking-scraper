import os
import time
import random
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

# 保存先
SAVE_DIR = "."
# ターゲットURL
TARGET_URL = "https://www.amazon.co.jp/gp/bestsellers/kitchen/"

def save_image(url, path):
    try:
        if not url: return False
        high_res_url = url.split("._")[0] + ".jpg"
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}
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
    html = f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Amazon LP Archive</title>
    <style>body{{font-family:sans-serif;background:#f4f4f4;padding:20px;color:#333}}.card{{background:white;margin-bottom:30px;padding:20px;border-radius:8px}}img{{max-height:200px;border:1px solid #ddd;border-radius:4px;margin:5px}}h1{{text-align:center}}.rank{{color:#e47911;font-weight:bold;font-size:1.2em}}</style></head><body><h1>Amazon LP Archive ({now_str})</h1>"""
    
    for r in results:
        subs = "".join([f'<a href="{s}" target="_blank"><img src="{s}"></a>' for s in r["subs"]])
        html += f'<div class="card"><div class="rank">No.{r["rank"]} <a href="{r["url"]}" target="_blank">{r["title"]}</a></div><br><div>メイン:<br><img src="{r["main"]}"></div><hr><div>LPサブ画像:<br>{subs if subs else "なし"}</div></div>'
    
    html += "</body></html>"
    with open(os.path.join(SAVE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

def run_scraper():
    if not os.path.exists(SAVE_DIR): os.makedirs(SAVE_DIR)
    
    with sync_playwright() as p:
        # ブラウザを起動
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36", locale="ja-JP")
        page = context.new_page()
        
        print("Amazonにアクセスします...")
        page.goto(TARGET_URL, wait_until="domcontentloaded")

        # ★★★ ここが新しいポイント！ ★★★
        print("\n" + "="*50)
        print("【重要】ブラウザを確認してください！")
        print("もし『ロボット確認画面』が出ていたら、手動でパズルを解いてください。")
        print("ランキング画面がちゃんと表示されたら、この画面に戻ってエンターキーを押してください。")
        print("="*50 + "\n")
        input("準備OKならここをクリックしてエンターキーを押す >> ")
        # ★★★★★★★★★★★★★★★★★★★★★

        items = page.query_selector_all(".p13n-sc-unpb-faceout")[:10]
        # レイアウト違い対応
        if not items: items = page.query_selector_all("[data-asin]")[:10]
        
        results = []
        print(f"{len(items)}件の商品が見つかりました。")

        for i, item in enumerate(items):
            rank = i + 1
            print(f"処理中: {rank}位...")
            
            link = item.query_selector("a.a-link-normal")
            if not link: continue
            
            title = item.query_selector(".p13n-sc-truncate-desktop-type2")
            title_text = title.inner_text() if title else f"Item {rank}"
            url = "https://www.amazon.co.jp" + link.get_attribute("href")
            
            main_img = f"rank{rank:02d}_main.jpg"
            img_el = item.query_selector("img")
            if img_el: save_image(img_el.get_attribute("src"), main_img)
            
            subs = []
            if rank <= 5: # 上位5件のみ詳細
                try:
                    p2 = context.new_page()
                    p2.goto(url, wait_until="domcontentloaded")
                    time.sleep(2)
                    
                    # サムネイル取得
                    thumbs = p2.query_selector_all("#altImages li.item.imageThumbnail")
                    for j, t in enumerate(thumbs[1:7]): # 2枚目〜7枚目
                        try:
                            t.hover()
                            time.sleep(0.5)
                            large = p2.query_selector("#landingImage, #imgTagWrapperId img")
                            if large:
                                s_name = f"rank{rank:02d}_{j+2:02d}.jpg"
                                if save_image(large.get_attribute("src"), s_name): subs.append(s_name)
                        except: pass
                    p2.close()
                except: pass
            
            results.append({"rank": rank, "title": title_text, "url": url, "main": main_img, "subs": subs})
            time.sleep(1)

        generate_html(results)
        print("完了！ git push してください。")
        browser.close()

if __name__ == "__main__":
    run_scraper()