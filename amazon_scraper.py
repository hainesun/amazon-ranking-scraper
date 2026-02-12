import os
import time
import requests
import shutil
from datetime import datetime
from playwright.sync_api import sync_playwright

# --- 設定エリア ---
BASE_DIR = "."
ARCHIVE_ROOT = "archives"
USER_DATA_DIR = "./my_browser_data"
BACKUP_DIR = None

# 複数のランキングターゲット
TARGETS = [
    {"name": "メンズバッグ・財布", "folder": "mens_bag_wallet", "url": "https://www.amazon.co.jp/gp/bestsellers/fashion/2221074051/"},
    {"name": "レディースバッグ", "folder": "ladies_bag", "url": "https://www.amazon.co.jp/gp/bestsellers/fashion/5355945051/"},
    {"name": "レディース財布", "folder": "ladies_wallet", "url": "https://www.amazon.co.jp/gp/bestsellers/fashion/2221186051/"},
    {"name": "メンズ財布", "folder": "mens_wallet_only", "url": "https://www.amazon.co.jp/gp/bestsellers/fashion/2221209051/"},
    {"name": "収納用品", "folder": "storage", "url": "https://www.amazon.co.jp/gp/bestsellers/kitchen/2491381051/"},
    {"name": "旅行用品", "folder": "travel", "url": "https://www.amazon.co.jp/gp/bestsellers/kitchen/2127357051/"}
]

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

def generate_html(all_data, save_dir, date_str):
    nav_html = get_date_links(date_str)
    toc_html = '<div class="toc"><strong>📂 カテゴリジャンプ:</strong> '
    for cat in all_data:
        toc_html += f'<a href="#{cat["folder"]}">{cat["name"]}</a> '
    toc_html += '</div>'

    html = f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Amazon Analysis - {date_str}</title>
    <style>
        body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f4f4f4;padding:20px;color:#333}}
        h1{{text-align:center;color:#232f3e; margin-bottom: 5px;}}
        .date-nav {{background: white; padding: 10px; margin-bottom: 10px; border-radius: 8px; text-align: center;}}
        .toc {{background: #232f3e; padding: 15px; margin-bottom: 30px; border-radius: 8px; text-align: center; color: white;}}
        .toc a {{color: white; background: #444; padding: 5px 10px; margin: 0 5px; text-decoration: none; border-radius: 4px; font-size: 0.9em; display:inline-block; margin-bottom:5px;}}
        .toc a:hover {{background: #e47911;}}
        .category-section {{background: white; padding: 20px; border-radius: 12px; margin-bottom: 50px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);}}
        .cat-title {{border-bottom: 3px solid #e47911; padding-bottom: 10px; margin-bottom: 20px; font-size: 1.5em; color: #232f3e;}}
        table {{width: 100%; border-collapse: collapse; table-layout: fixed;}}
        th, td {{border: 1px solid #ddd; padding: 10px; vertical-align: top;}}
        th {{background: #f0f2f2; color: #333; text-align: left;}}
        .col-rank {{width: 40px; text-align: center; font-weight: bold; font-size: 1.2em; color: #e47911;}}
        .col-main {{width: 130px; text-align: center;}}
        .col-info {{width: 180px; word-wrap: break-word; font-size: 0.9em;}}
        .main-img {{width: 110px; border: 1px solid #eee;}}
        .lp-gallery {{display: flex; gap: 5px; overflow-x: auto; padding-bottom: 5px;}}
        .lp-gallery img {{height: 100px; border: 1px solid #ccc; border-radius: 4px; transition: transform 0.2s;}}
        .lp-gallery img:hover {{transform: scale(1.1); border-color: #e47911;}}
        a {{text-decoration: none; color: #007185; font-weight: bold;}}
    </style></head><body>
    <h1>Amazon LP Daily Archive</h1>
    <p style="text-align:center; color:#666;">{date_str}</p>
    {nav_html}
    {toc_html}
    """
    
    for cat in all_data:
        html += f"""
        <div id="{cat['folder']}" class="category-section">
            <h2 class="cat-title">📦 {cat['name']}</h2>
            <table>
                <thead>
                    <tr><th style="width:40px;">#</th><th style="width:130px;">Main</th><th>Info</th><th>LP Gallery</th></tr>
                </thead>
                <tbody>
        """
        for r in cat["results"]:
            main_path = f"{cat['folder']}/{r['main']}"
            subs_html = ""
            for s in r['subs']:
                s_path = f"{cat['folder']}/{s}"
                subs_html += f'<a href="{s_path}" target="_blank"><img src="{s_path}"></a>'

            html += f"""
            <tr>
                <td class="col-rank">{r["rank"]}</td>
                <td class="col-main"><a href="{main_path}" target="_blank"><img src="{main_path}" class="main-img"></a></td>
                <td class="col-info"><a href="{r['url']}" target="_blank">{r['title']}</a></td>
                <td class="col-lp"><div class="lp-gallery">{subs_html if subs_html else "<span style='color:#999;font-size:0.8em'>-</span>"}</div></td>
            </tr>
            """
        html += "</tbody></table></div>"

    html += "</body></html>"
    with open(os.path.join(save_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

def update_root_index():
    if not os.path.exists(ARCHIVE_ROOT): return
    dates = sorted([d for d in os.listdir(ARCHIVE_ROOT) if os.path.isdir(os.path.join(ARCHIVE_ROOT, d))], reverse=True)
    if not dates: return
    latest_date = dates[0]
    html = f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><meta http-equiv="refresh" content="0; url={ARCHIVE_ROOT}/{latest_date}/index.html"><title>Redirecting...</title></head><body>Redirecting... <a href="{ARCHIVE_ROOT}/{latest_date}/index.html">Click here</a></body></html>"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

def run_scraper():
    today_str = datetime.now().strftime('%Y-%m-%d')
    daily_root_dir = os.path.join(ARCHIVE_ROOT, today_str)
    if not os.path.exists(daily_root_dir): os.makedirs(daily_root_dir)
    
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(user_data_dir=USER_DATA_DIR, headless=False, channel="chrome", viewport={"width": 1280, "height": 900}, user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
        page = browser.pages[0]
        
        print("\n" + "="*60 + "\n🚀 マルチカテゴリ収集を開始します\n" + "="*60)
        
        all_categories_data = []

        for idx, target in enumerate(TARGETS):
            print(f"\n[{idx+1}/{len(TARGETS)}] カテゴリ: {target['name']} をスキャン中...")
            
            # 1. ページを開く
            try:
                page.goto(target['url'], wait_until="domcontentloaded")
            except:
                print("読み込みタイムアウト（続行）")

            # 2. ロボット確認（初回のみ手動介入）
            items = []
            selectors = [".p13n-sc-unpb-faceout", "#gridItemRoot", ".zg-grid-general-faceout", "div[id^='p13n-asin-index']"]
            
            # 自動で見つからなければユーザーに聞く
            retry = 0
            while retry < 2:
                for sel in selectors:
                    found = page.query_selector_all(sel)
                    if len(found) > 0: items = found[:10]; break
                
                if len(items) > 0: break
                
                print("⚠️ 商品が見つかりません。ロボット確認画面が出ていたら手動でクリアしてください。")
                print("ランキングが表示されているのを確認したら、エンターを押してください。")
                input(">> ")
                retry += 1
            
            if len(items) == 0:
                print(f"❌ スキップします: {target['name']}")
                continue

            # 3. ★ここが新しい！先にデータだけ全部メモする（エラー回避）
            print(f"  -> {len(items)}件の情報をメモしています...")
            scan_data = []
            
            for i, item in enumerate(items):
                try:
                    rank = i + 1
                    link = item.query_selector("a.a-link-normal") or item.query_selector("a")
                    if not link: continue
                    
                    url_part = link.get_attribute("href")
                    full_url = "https://www.amazon.co.jp" + url_part if not url_part.startswith("http") else url_part
                    
                    title_el = item.query_selector(".p13n-sc-truncate-desktop-type2") or item.query_selector("div[class*='truncate']")
                    title = title_el.inner_text().strip() if title_el else f"Item {rank}"
                    
                    img_el = item.query_selector("img")
                    img_src = img_el.get_attribute("src") if img_el else ""
                    
                    # メモに追加
                    scan_data.append({
                        "rank": rank,
                        "title": title,
                        "url": full_url,
                        "img_src": img_src
                    })
                except:
                    continue
            
            # 4. メモをもとに、1件ずつゆっくり画像を保存しにいく
            print(f"  -> {len(scan_data)}件の詳細画像を取得中...")
            cat_dir = os.path.join(daily_root_dir, target['folder'])
            if not os.path.exists(cat_dir): os.makedirs(cat_dir)
            
            results = []
            for data in scan_data:
                # メイン画像保存
                main_img_name = f"rank{data['rank']:02d}_main.jpg"
                save_image(data['img_src'], os.path.join(cat_dir, main_img_name))
                
                # 詳細ページでサブ画像取得（上位3位のみ）
                subs = []
                if data['rank'] <= 3:
                    try:
                        p2 = browser.new_page()
                        p2.goto(data['url'], wait_until="domcontentloaded")
                        time.sleep(1.5)
                        
                        thumbs = p2.query_selector_all("#altImages li.item.imageThumbnail img")
                        for j, img in enumerate(thumbs[1:7]):
                            src = img.get_attribute("src")
                            if src:
                                s_name = f"rank{data['rank']:02d}_{j+2:02d}.jpg"
                                if save_image(src, os.path.join(cat_dir, s_name)): subs.append(s_name)
                        p2.close()
                    except:
                        if not p2.is_closed(): p2.close()
                
                results.append({
                    "rank": data['rank'],
                    "title": data['title'],
                    "url": data['url'],
                    "main": main_img_name,
                    "subs": subs
                })
                print(f"    - {data['rank']}位 完了")
                time.sleep(1) # やさしく

            all_categories_data.append({"name": target['name'], "folder": target['folder'], "results": results})
            time.sleep(2)

        generate_html(all_categories_data, daily_root_dir, today_str)
        update_root_index()
        
        print(f"\n🎉 全カテゴリ完了！ git push してください。")
        browser.close()

if __name__ == "__main__":
    run_scraper()