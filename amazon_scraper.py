import os
import time
import random
import requests
import shutil
from datetime import datetime
from playwright.sync_api import sync_playwright

# --- 設定エリア ---
BASE_DIR = "."
ARCHIVE_ROOT = "archives"
USER_DATA_DIR = "./my_browser_data"
BACKUP_DIR = None

# ターゲット設定
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

# --- 日付リンク生成（復活！） ---
def get_date_links(current_date_str):
    if not os.path.exists(ARCHIVE_ROOT): return ""
    
    # フォルダがある日付を取得してソート
    dates = sorted([d for d in os.listdir(ARCHIVE_ROOT) if os.path.isdir(os.path.join(ARCHIVE_ROOT, d))], reverse=True)
    
    html = '<div class="date-nav-bar"><span class="nav-label">📅 履歴:</span> '
    for d in dates:
        if d == current_date_str:
            html += f'<span class="nav-current">{d}</span> '
        else:
            # 同じ階層の別フォルダへ移動
            html += f'<a href="../{d}/index.html" class="nav-link">{d}</a> '
    html += '</div>'
    return html

# --- ルートのインデックスページ（ダッシュボード） ---
def update_root_index():
    if not os.path.exists(ARCHIVE_ROOT): return
    dates = sorted([d for d in os.listdir(ARCHIVE_ROOT) if os.path.isdir(os.path.join(ARCHIVE_ROOT, d))], reverse=True)
    
    links_html = ""
    for d in dates:
        links_html += f"""
        <a href="{ARCHIVE_ROOT}/{d}/index.html" class="date-card">
            <span class="icon">📁</span>
            <span class="date-text">{d}</span>
            <span class="arrow">→</span>
        </a>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Amazon LP Research Dashboard</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f0f2f5; color: #333; margin: 0; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            header {{ text-align: center; margin-bottom: 40px; padding: 20px 0; }}
            h1 {{ color: #232f3e; margin: 0; font-size: 24px; }}
            p {{ color: #666; margin-top: 10px; }}
            .dashboard-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; }}
            .date-card {{ 
                display: flex; align-items: center; justify-content: space-between;
                background: white; padding: 20px; border-radius: 12px; 
                text-decoration: none; color: #333; 
                box-shadow: 0 2px 5px rgba(0,0,0,0.05); transition: transform 0.2s, box-shadow 0.2s; 
                border-left: 5px solid #e47911;
            }}
            .date-card:hover {{ transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
            .date-text {{ font-weight: bold; font-size: 18px; }}
            .icon {{ font-size: 20px; margin-right: 10px; }}
            .arrow {{ color: #ccc; }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Amazon LP Research Dashboard</h1>
                <p>収集したランキングデータのアーカイブ一覧</p>
            </header>
            <div class="dashboard-grid">
                {links_html}
            </div>
        </div>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

# --- 日次レポートページ生成 ---
def generate_html(all_data, save_dir, date_str):
    # 日付ナビゲーションを取得
    date_nav_html = get_date_links(date_str)
    
    # 目次
    toc_html = '<div class="toc"><strong>📂 カテゴリ:</strong> '
    for cat in all_data:
        toc_html += f'<a href="#{cat["folder"]}">{cat["name"]}</a> '
    toc_html += '</div>'

    html = f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Amazon Report {date_str}</title>
    <style>
        body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f4f4f4;padding:20px;color:#333; margin:0;}}
        .container {{max-width: 1400px; margin: 0 auto;}}
        
        .header-area {{text-align:center; margin-bottom:20px;}}
        h1 {{color:#232f3e; margin:0; font-size:24px;}}
        .home-link {{display:inline-block; margin-top:5px; color:#007185; text-decoration:none; font-size:0.9em;}}
        
        /* 日付ナビゲーションバー */
        .date-nav-bar {{background:white; padding:10px; margin-bottom:15px; border-radius:8px; text-align:center; font-size:0.9em; overflow-x:auto; white-space:nowrap;}}
        .nav-label {{font-weight:bold; color:#555; margin-right:5px;}}
        .nav-link {{display:inline-block; padding:4px 8px; margin:0 2px; color:#007185; text-decoration:none; border:1px solid #ddd; border-radius:4px;}}
        .nav-link:hover {{background:#e47911; color:white; border-color:#e47911;}}
        .nav-current {{display:inline-block; padding:4px 8px; margin:0 2px; background:#232f3e; color:white; border-radius:4px; font-weight:bold;}}

        .toc {{background:white; padding:15px; margin-bottom:30px; border-radius:8px; text-align:center; box-shadow:0 2px 5px rgba(0,0,0,0.05); position:sticky; top:10px; z-index:90;}}
        .toc a {{color:#333; background:#f0f2f5; padding:6px 12px; margin:4px; text-decoration:none; border-radius:20px; font-size:0.9em; display:inline-block; transition:0.2s;}}
        .toc a:hover {{background:#232f3e; color:white;}}

        .category-section {{background:white; padding:20px; border-radius:12px; margin-bottom:40px; box-shadow:0 2px 8px rgba(0,0,0,0.08);}}
        .cat-title {{border-bottom:2px solid #e47911; padding-bottom:10px; margin-bottom:15px; font-size:1.4em; color:#232f3e; display:flex; align-items:center;}}
        .cat-icon {{margin-right:10px;}}

        table {{width:100%; border-collapse:collapse; table-layout:fixed;}}
        th, td {{border-bottom:1px solid #eee; padding:12px 8px; vertical-align:top;}}
        th {{background:#f9f9f9; color:#555; text-align:left; font-size:0.85em; font-weight:bold;}}
        .col-rank {{width:50px; text-align:center; font-weight:bold; font-size:1.4em; color:#e47911;}}
        .col-main {{width:140px; text-align:center;}}
        .col-info {{width:250px; font-size:0.9em; line-height:1.5;}}
        .main-img {{width:120px; height:auto; border-radius:4px; border:1px solid #eee; transition:transform 0.2s; cursor:pointer;}}
        .main-img:hover {{transform:scale(1.05);}}
        .lp-gallery {{display:flex; flex-wrap:wrap; gap:8px;}}
        .lp-thumb {{height:100px; width:auto; border-radius:4px; border:1px solid #ddd; cursor:zoom-in; transition:0.2s;}}
        .lp-thumb:hover {{border-color:#e47911; transform:translateY(-2px);}}
        .product-title {{font-weight:bold; color:#007185; text-decoration:none; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;}}
        .no-lp {{color:#ccc; font-size:0.8em; font-style:italic;}}

        .modal {{display:none; position:fixed; z-index:1000; left:0; top:0; width:100%; height:100%; overflow:auto; background-color:rgba(0,0,0,0.85);}}
        .modal-content {{margin:auto; display:block; max-width:90%; max-height:90vh; margin-top:3vh;}}
        .close {{position:absolute; top:20px; right:35px; color:#f1f1f1; font-size:40px; font-weight:bold; cursor:pointer;}}
    </style>
    </head>
    <body>
        <div class="container">
            <div class="header-area">
                <a href="../../index.html" class="home-link">← ダッシュボードに戻る</a>
                <h1>Amazon LP Daily Report</h1>
                <div style="color:#666; font-size:0.9em; margin-bottom:10px;">{date_str}</div>
                {date_nav_html} </div>
            {toc_html}
    """
    
    for cat in all_data:
        html += f"""
        <div id="{cat['folder']}" class="category-section">
            <h2 class="cat-title"><span class="cat-icon">📦</span> {cat['name']}</h2>
            <table>
                <thead>
                    <tr><th style="width:50px;">Rank</th><th style="width:140px;">Thumb</th><th style="width:250px;">Product Info</th><th>LP Gallery (Click to Zoom)</th></tr>
                </thead>
                <tbody>
        """
        for r in cat["results"]:
            main_path = f"{cat['folder']}/{r['main']}"
            subs_html = ""
            for s in r['subs']:
                s_path = f"{cat['folder']}/{s}"
                subs_html += f'<img src="{s_path}" class="lp-thumb" onclick="openModal(this.src)">'
            if not subs_html: subs_html = '<span class="no-lp">No LP Images (Top 5 Only)</span>'

            display_title = r['title'] if r['title'] and r['title'] != "Item 1" else "商品タイトル取得不可"

            html += f"""
            <tr>
                <td class="col-rank">{r["rank"]}</td>
                <td class="col-main"><img src="{main_path}" class="main-img" onclick="openModal(this.src)"></td>
                <td class="col-info">
                    <a href="{r['url']}" target="_blank" class="product-title">{display_title}</a>
                    <div style="margin-top:8px;">
                        <a href="{r['url']}" target="_blank" style="font-size:0.85em; color:#555; text-decoration:none;">🔗 Amazonで見る</a>
                    </div>
                </td>
                <td class="col-lp"><div class="lp-gallery">{subs_html}</div></td>
            </tr>
            """
        html += "</tbody></table></div>"

    html += """
        </div>
        <div id="imageModal" class="modal" onclick="closeModal()">
            <span class="close">&times;</span>
            <img class="modal-content" id="modalImg">
        </div>
        <script>
            function openModal(src) {
                document.getElementById("imageModal").style.display = "block";
                document.getElementById("modalImg").src = src;
                document.body.style.overflow = "hidden";
            }
            function closeModal() {
                document.getElementById("imageModal").style.display = "none";
                document.body.style.overflow = "auto";
            }
            document.addEventListener('keydown', function(event) { if (event.key === "Escape") closeModal(); });
        </script>
    </body></html>
    """
    with open(os.path.join(save_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

def run_scraper():
    today_str = datetime.now().strftime('%Y-%m-%d')
    daily_root_dir = os.path.join(ARCHIVE_ROOT, today_str)
    if not os.path.exists(daily_root_dir): os.makedirs(daily_root_dir)
    
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(user_data_dir=USER_DATA_DIR, headless=False, channel="chrome", viewport={"width": 1280, "height": 900}, user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
        page = browser.pages[0]
        
        print("\n" + "="*60 + "\n🚀 マルチカテゴリ収集開始 (V2.1)\n" + "="*60)
        
        all_categories_data = []

        for idx, target in enumerate(TARGETS):
            print(f"\n[{idx+1}/{len(TARGETS)}] カテゴリ: {target['name']} をスキャン中...")
            try: page.goto(target['url'], wait_until="domcontentloaded")
            except: print("読み込みタイムアウト（続行）")

            items = []
            selectors = [".p13n-sc-unpb-faceout", "#gridItemRoot", ".zg-grid-general-faceout", "div[id^='p13n-asin-index']"]
            retry = 0
            while retry < 2:
                for sel in selectors:
                    found = page.query_selector_all(sel)
                    if len(found) > 0: items = found[:10]; break
                if len(items) > 0: break
                print("⚠️ ロボット確認画面が出ていたら手動でクリアしてください。")
                input("準備ができたらエンターキーを押してください >> ")
                retry += 1
            
            if len(items) == 0:
                print(f"❌ スキップします: {target['name']}")
                continue

            print(f"  -> {len(items)}件の情報をメモしています...")
            scan_data = []
            for i, item in enumerate(items):
                try:
                    rank = i + 1
                    link = item.query_selector("a.a-link-normal") or item.query_selector("a")
                    if not link: continue
                    url_part = link.get_attribute("href")
                    full_url = "https://www.amazon.co.jp" + url_part if not url_part.startswith("http") else url_part
                    
                    # タイトル取得ロジック
                    title = "Item"
                    t1 = item.query_selector(".p13n-sc-truncate-desktop-type2") or item.query_selector("div[class*='truncate']")
                    if t1: title = t1.inner_text().strip()
                    else:
                        img_tag = item.query_selector("img")
                        if img_tag and img_tag.get_attribute("alt"): title = img_tag.get_attribute("alt")
                        elif link.inner_text().strip(): title = link.inner_text().strip()

                    img_el = item.query_selector("img")
                    img_src = img_el.get_attribute("src") if img_el else ""
                    scan_data.append({"rank": rank, "title": title, "url": full_url, "img_src": img_src})
                except: continue
            
            print(f"  -> 画像を取得中...")
            cat_dir = os.path.join(daily_root_dir, target['folder'])
            if not os.path.exists(cat_dir): os.makedirs(cat_dir)
            
            results = []
            for data in scan_data:
                main_img_name = f"rank{data['rank']:02d}_main.jpg"
                save_image(data['img_src'], os.path.join(cat_dir, main_img_name))
                subs = []
                if data['rank'] <= 5:
                    try:
                        p2 = browser.new_page()
                        p2.goto(data['url'], wait_until="domcontentloaded")
                        time.sleep(1.5)
                        for j, img in enumerate(p2.query_selector_all("#altImages li.item.imageThumbnail img")[1:7]):
                            src = img.get_attribute("src")
                            if src:
                                s_name = f"rank{data['rank']:02d}_{j+2:02d}.jpg"
                                if save_image(src, os.path.join(cat_dir, s_name)): subs.append(s_name)
                        p2.close()
                        print(f"    - {data['rank']}位 完了", end="\r")
                    except: 
                        if not p2.is_closed(): p2.close()
                results.append({"rank": data['rank'], "title": data['title'], "url": data['url'], "main": main_img_name, "subs": subs})
                if data['rank'] <= 5: time.sleep(random.uniform(1, 2))

            print("")
            all_categories_data.append({"name": target['name'], "folder": target['folder'], "results": results})
            time.sleep(2)

        generate_html(all_categories_data, daily_root_dir, today_str)
        update_root_index()
        print(f"\n🎉 全行程完了！ git push してください。")
        browser.close()

if __name__ == "__main__":
    run_scraper()