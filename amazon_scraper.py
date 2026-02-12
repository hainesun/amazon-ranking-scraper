import os
import time
import requests
import shutil
from datetime import datetime
from playwright.sync_api import sync_playwright

# --- 設定 ---
BASE_DIR = "."
ARCHIVE_ROOT = "archives" # データを貯める場所
TARGET_URL = "https://www.amazon.co.jp/gp/bestsellers/kitchen/"
USER_DATA_DIR = "./my_browser_data"

# ★Googleドライブ自動バックアップは「なし」に設定
BACKUP_DIR = None 

def save_image(url, path):
    try:
        if not url: return False
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

def get_date_links(current_date_str):
    links_html = '<div class="date-nav"><strong>📅 日付を選択: </strong>'
    dates = []
    if os.path.exists(ARCHIVE_ROOT):
        for d in os.listdir(ARCHIVE_ROOT):
            if os.path.isdir(os.path.join(ARCHIVE_ROOT, d)):
                dates.append(d)
    dates.sort(reverse=True)
    for d in dates:
        if d == current_date_str:
            links_html += f'<span class="current-date">{d}</span> '
        else:
            links_html += f'<a href="../../{ARCHIVE_ROOT}/{d}/index.html" class="date-link">{d}</a> '
    links_html += '</div>'
    return links_html

def generate_html(results, save_dir, date_str):
    nav_html = get_date_links(date_str)
    html = f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Amazon LP Archive - {date_str}</title>
    <style>
        body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f9f9f9;padding:20px;color:#333}}
        h1{{text-align:center;margin-bottom:10px;color:#232f3e}}
        .date-nav {{background: white; padding: 15px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center;}}
        .date-link {{display: inline-block; padding: 5px 10px; margin: 0 5px; background: #eee; color: #333; text-decoration: none; border-radius: 4px; font-size: 0.9em;}}
        .date-link:hover {{background: #e47911; color: white;}}
        .current-date {{display: inline-block; padding: 5px 10px; margin: 0 5px; background: #232f3e; color: white; border-radius: 4px; font-weight: bold;}}
        table {{width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1); table-layout: fixed;}}
        th, td {{border: 1px solid #ddd; padding: 10px; vertical-align: top;}}
        th {{background: #232f3e; color: white; text-align: left; padding: 12px;}}
        .col-rank {{width: 50px; text-align: center; font-weight: bold; font-size: 1.4em; color: #e47911;}}
        .col-main {{width: 140px; text-align: center;}}
        .col-info {{width: 200px; word-wrap: break-word;}}
        .main-img {{width: 120px; border: 1px solid #eee;}}
        .lp-gallery {{display: flex; gap: 8px; overflow-x: auto; padding-bottom: 5px;}}
        .lp-gallery img {{height: 110px; border: 1px solid #ccc; border-radius: 4px; transition: transform 0.2s; cursor: pointer;}}
        .lp-gallery img:hover {{transform: scale(1.1); border-color: #e47911;}}
        a {{text-decoration: none; color: #007185; font-weight: bold; font-size: 0.95em;}}
        a:hover {{text-decoration: underline; color: #c7511f;}}
    </style></head><body>
    <h1>Amazon LP Archive ({date_str})</h1>
    {nav_html}
    <table>
        <thead>
            <tr><th style="width:50px;">#</th><th style="width:140px;">Main</th><th style="width:200px;">Info</th><th>LP Gallery</th></tr>
        </thead>
        <tbody>
    """
    for r in results:
        subs_html = "".join([f'<a href="{s}" target="_blank"><img src="{s}"></a>' for s in r["subs"]])
        html += f"""
        <tr>
            <td class="col-rank">{r["rank"]}</td>
            <td class="col-main"><a href="{r['main']}" target="_blank"><img src="{r['main']}" class="main-img"></a></td>
            <td class="col-info"><a href="{r['url']}" target="_blank">{r['title']}</a></td>
            <td class="col-lp"><div class="lp-gallery">{subs_html if subs_html else "<span style='color:#999;font-size:0.8em'>No Sub Images</span>"}</div></td>
        </tr>
        """
    html += "</tbody></table></body></html>"
    with open(os.path.join(save_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

def update_root_index():
    if not os.path.exists(ARCHIVE_ROOT): return
    dates = sorted([d for d in os.listdir(ARCHIVE_ROOT) if os.path.isdir(os.path.join(ARCHIVE_ROOT, d))], reverse=True)
    if not dates: return
    latest_date = dates[0]
    html = f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><meta http-equiv="refresh" content="0; url={ARCHIVE_ROOT}/{latest_date}/index.html"><title>Redirecting...</title></head><body><p>最新のレポートに移動します... <a href="{ARCHIVE_ROOT}/{latest_date}/index.html">クリックして移動</a></p></body></html>"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

def run_scraper():
    today_str = datetime.now().strftime('%Y-%m-%d')
    daily_save_dir = os.path.join(ARCHIVE_ROOT, today_str)
    if not os.path.exists(daily_save_dir): os.makedirs(daily_save_dir)
    
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(user_data_dir=USER_DATA_DIR, headless=False, channel="chrome", viewport={"width": 1280, "height": 900}, user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
        page = browser.pages[0]
        
        print(f"[{today_str}] Amazonにアクセスします...")
        try:
            page.goto(TARGET_URL, wait_until="domcontentloaded")
        except: pass

        print("\n" + "="*50 + "\n【確認】ランキングが表示されたらエンターキーを押してください\n" + "="*50 + "\n")
        input("準備OKならエンターキーを押す >> ")

        selectors = [".p13n-sc-unpb-faceout", "#gridItemRoot", ".zg-grid-general-faceout", "div[id^='p13n-asin-index']"]
        items = []
        for sel in selectors:
            found = page.query_selector_all(sel)
            if len(found) > 0: items = found[:10]; break
        
        print(f"{len(items)}件の商品を処理します。")
        results = []

        for i, item in enumerate(items):
            rank = i + 1
            print(f"処理中: {rank}位...")
            link = item.query_selector("a.a-link-normal")
            if not link: link = item.query_selector("a")
            if not link: continue
            
            url_part = link.get_attribute("href")
            url = "https://www.amazon.co.jp" + url_part if not url_part.startswith("http") else url_part
            title_el = item.query_selector(".p13n-sc-truncate-desktop-type2")
            if not title_el: title_el = item.query_selector("div[class*='truncate']")
            title_text = title_el.inner_text().strip() if title_el else f"Item {rank}"
            
            main_img_name = f"rank{rank:02d}_main.jpg"
            img_el = item.query_selector("img")
            if img_el: save_image(img_el.get_attribute("src"), os.path.join(daily_save_dir, main_img_name))
            
            subs = []
            if rank <= 3: 
                try:
                    p2 = browser.new_page(); p2.goto(url, wait_until="domcontentloaded"); time.sleep(2)
                    for j, img in enumerate(p2.query_selector_all("#altImages li.item.imageThumbnail img")[1:7]):
                        s_name = f"rank{rank:02d}_{j+2:02d}.jpg"
                        if save_image(img.get_attribute("src"), os.path.join(daily_save_dir, s_name)): subs.append(s_name)
                    p2.close()
                except: 
                     if not p2.is_closed(): p2.close()
            results.append({"rank": rank, "title": title_text, "url": url, "main": main_img_name, "subs": subs})
            time.sleep(1)

        generate_html(results, daily_save_dir, today_str)
        update_root_index()
        
        print(f"\n🎉 完了！本日のデータは 'archives/{today_str}' に保存されました。")
        print("git push してください。")
        browser.close()

if __name__ == "__main__":
    run_scraper()