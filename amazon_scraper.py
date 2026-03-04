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

# ★全8ジャンルのターゲット設定
TARGETS = [
    {"name": "メンズバッグ・財布", "folder": "mens_bag_wallet", "url": "https://www.amazon.co.jp/gp/bestsellers/fashion/2221074051/"},
    {"name": "レディースバッグ", "folder": "ladies_bag", "url": "https://www.amazon.co.jp/gp/bestsellers/fashion/5355945051/"},
    {"name": "レディース財布", "folder": "ladies_wallet", "url": "https://www.amazon.co.jp/gp/bestsellers/fashion/2221186051/"},
    {"name": "メンズ財布", "folder": "mens_wallet_only", "url": "https://www.amazon.co.jp/gp/bestsellers/fashion/2221209051/"},
    {"name": "ファッション小物", "folder": "fashion_goods", "url": "https://www.amazon.co.jp/gp/bestsellers/fashion/5651345051/"},
    {"name": "ベビー用品", "folder": "baby_goods", "url": "https://www.amazon.co.jp/gp/bestsellers/baby/345962011/"},
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
    if not os.path.exists(ARCHIVE_ROOT): return ""
    dates = sorted([d for d in os.listdir(ARCHIVE_ROOT) if os.path.isdir(os.path.join(ARCHIVE_ROOT, d))], reverse=True)
    html = '<div class="date-nav-bar"><span class="nav-label">📅 履歴:</span> '
    for d in dates:
        if d == current_date_str:
            html += f'<span class="nav-current">{d}</span> '
        else:
            html += f'<a href="../{d}/index.html" class="nav-link">{d}</a> '
    html += '</div>'
    return html

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
    html = f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Amazon LP Dashboard</title><style>body {{ font-family: -apple-system, sans-serif; background-color: #f0f2f5; color: #333; padding: 20px; }}.container {{ max-width: 800px; margin: 0 auto; }}header {{ text-align: center; margin-bottom: 40px; padding: 20px 0; }}h1 {{ color: #232f3e; margin: 0; }}.dashboard-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; }}.date-card {{ display: flex; align-items: center; justify-content: space-between; background: white; padding: 20px; border-radius: 12px; text-decoration: none; color: #333; box-shadow: 0 2px 5px rgba(0,0,0,0.05); transition: 0.2s; border-left: 5px solid #e47911; }}.date-card:hover {{ transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}</style></head><body><div class="container"><header><h1>Amazon LP Research Dashboard</h1><p>収集したランキングデータのアーカイブ一覧</p></header><div class="dashboard-grid">{links_html}</div></div></body></html>"""
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

# --- ① 詳細レポート（Top 10）の生成 ---
def generate_detail_html(all_data, save_dir, date_str):
    date_nav_html = get_date_links(date_str)
    toc_html = '<div class="toc"><strong>📂 カテゴリ:</strong> '
    for cat in all_data: toc_html += f'<a href="#{cat["folder"]}">{cat["name"]}</a> '
    toc_html += '</div>'

    html = f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><title>LP Report {date_str}</title>
    <style>
        body{{font-family:-apple-system,sans-serif;background:#f4f4f4;padding:20px;color:#333;margin:0;}}
        .container {{max-width: 1400px; margin: 0 auto;}}
        .header-area {{text-align:center; margin-bottom:20px;}}
        h1 {{color:#232f3e; margin:0; font-size:24px;}}
        .home-link {{display:inline-block; margin-top:5px; color:#007185; text-decoration:none;}}
        
        /* タブ切り替えボタン */
        .tabs {{display:flex; justify-content:center; gap:15px; margin: 20px 0;}}
        .tab {{padding: 12px 25px; text-decoration:none; font-weight:bold; border-radius:8px; font-size:1.1em; transition:0.2s; box-shadow: 0 2px 5px rgba(0,0,0,0.1);}}
        .tab-active {{background:#e47911; color:white; border:2px solid #e47911;}}
        .tab-inactive {{background:white; color:#333; border:2px solid #ddd;}}
        .tab-inactive:hover {{background:#f0f2f5; border-color:#aaa;}}

        .date-nav-bar {{background:white; padding:10px; margin-bottom:15px; border-radius:8px; text-align:center; font-size:0.9em;}}
        .nav-label {{font-weight:bold; color:#555; margin-right:5px;}}
        .nav-link {{padding:4px 8px; color:#007185; text-decoration:none; border:1px solid #ddd; border-radius:4px;}}
        .nav-current {{padding:4px 8px; background:#232f3e; color:white; border-radius:4px; font-weight:bold;}}
        .toc {{background:white; padding:15px; margin-bottom:30px; border-radius:8px; text-align:center; position:sticky; top:10px; z-index:90; box-shadow:0 2px 5px rgba(0,0,0,0.05);}}
        .toc a {{color:#333; background:#f0f2f5; padding:6px 12px; margin:4px; text-decoration:none; border-radius:20px; display:inline-block; transition:0.2s;}}
        .toc a:hover {{background:#232f3e; color:white;}}
        .category-section {{background:white; padding:20px; border-radius:12px; margin-bottom:40px; box-shadow:0 2px 8px rgba(0,0,0,0.08);}}
        .cat-title {{border-bottom:2px solid #e47911; padding-bottom:10px; margin-bottom:15px; font-size:1.4em; color:#232f3e;}}
        table {{width:100%; border-collapse:collapse; table-layout:fixed;}}
        th, td {{border-bottom:1px solid #eee; padding:12px 8px; vertical-align:top;}}
        th {{background:#f9f9f9; color:#555; text-align:left;}}
        .col-rank {{width:50px; text-align:center; font-weight:bold; font-size:1.4em; color:#e47911;}}
        .col-main {{width:130px; text-align:center;}}
        .col-info {{width:220px; font-size:0.9em; line-height:1.5;}}
        .main-img {{width:110px; height:auto; border-radius:4px; border:1px solid #eee; cursor:pointer;}}
        .lp-gallery {{display: flex; flex-wrap: wrap; gap: 5px;}}
        .lp-thumb {{height: 80px; width: auto; border-radius:4px; border:1px solid #ddd; cursor:zoom-in; transition:0.2s;}}
        .lp-thumb:hover {{border-color:#e47911; transform:scale(1.05); z-index:1;}}
        .product-title {{font-weight:bold; color:#007185; text-decoration:none; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;}}
        .modal {{display:none; position:fixed; z-index:1000; left:0; top:0; width:100%; height:100%; overflow:auto; background-color:rgba(0,0,0,0.85);}}
        .modal-content {{margin:auto; display:block; max-width:90%; max-height:90vh; margin-top:3vh;}}
        .close {{position:absolute; top:20px; right:35px; color:#f1f1f1; font-size:40px; font-weight:bold; cursor:pointer;}}
    </style></head><body>
    <div class="container">
        <div class="header-area">
            <a href="../../index.html" class="home-link">← ダッシュボードに戻る</a>
            <h1>Amazon Daily Report ({date_str})</h1>
            {date_nav_html}
            
            <div class="tabs">
                <a href="index.html" class="tab tab-active">📊 LP詳細レポート (Top 10)</a>
                <a href="thumbnail_board.html" class="tab tab-inactive">📸 サムネイル一覧 (Top 50)</a>
            </div>
        </div>
        {toc_html}
    """
    
    for cat in all_data:
        html += f'<div id="{cat["folder"]}" class="category-section"><h2 class="cat-title">📦 {cat["name"]} (Top 10)</h2><table><thead><tr><th style="width:50px;">Rank</th><th style="width:130px;">Thumb</th><th style="width:220px;">Product Info</th><th>LP Gallery</th></tr></thead><tbody>'
        
        # トップ10だけ表示
        for r in cat["items"][:10]:
            main_path = f"{cat['folder']}/{r['main']}"
            subs_html = "".join([f'<img src="{cat["folder"]}/{s}" class="lp-thumb" onclick="openModal(this.src)">' for s in r['subs']])
            if not subs_html: subs_html = '<span style="color:#ccc; font-size:0.8em">LP画像なし</span>'
            title = r['title'] if r['title'] and r['title'] != "Item 1" else "商品タイトル取得不可"

            html += f'<tr><td class="col-rank">{r["rank"]}</td><td class="col-main"><img src="{main_path}" class="main-img" onclick="openModal(this.src)"></td><td class="col-info"><a href="{r["url"]}" target="_blank" class="product-title">{title}</a><div style="margin-top:8px;"><a href="{r["url"]}" target="_blank" style="font-size:0.85em; color:#555; text-decoration:none;">🔗 Amazonで見る</a></div></td><td class="col-lp"><div class="lp-gallery">{subs_html}</div></td></tr>'
        html += "</tbody></table></div>"

    html += """</div>
    <div id="imageModal" class="modal" onclick="closeModal()"><span class="close">&times;</span><img class="modal-content" id="modalImg"></div>
    <script>
        function openModal(src) { document.getElementById("imageModal").style.display = "block"; document.getElementById("modalImg").src = src; document.body.style.overflow = "hidden"; }
        function closeModal() { document.getElementById("imageModal").style.display = "none"; document.body.style.overflow = "auto"; }
        document.addEventListener('keydown', function(event) { if (event.key === "Escape") closeModal(); });
    </script></body></html>"""
    
    with open(os.path.join(save_dir, "index.html"), "w", encoding="utf-8") as f: f.write(html)


# --- ② サムネイル一覧（Top 50）の生成 ---
def generate_thumbnail_html(all_data, save_dir, date_str):
    toc_html = '<div class="toc"><strong>📂 カテゴリ:</strong> '
    for cat in all_data: toc_html += f'<a href="#{cat["folder"]}">{cat["name"]}</a> '
    toc_html += '</div>'

    html = f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><title>Thumbnail Board {date_str}</title>
    <style>
        body {{background: #1a1a1a; color: #fff; font-family: -apple-system, sans-serif; padding: 20px; text-align: center; margin: 0;}}
        .header-area {{margin-bottom: 20px;}}
        h1 {{color: #e47911; margin: 0; font-size: 24px;}}
        .home-link {{display:inline-block; margin-top:5px; color:#4db8ff; text-decoration:none;}}
        
        /* タブ切り替え（ダークモード用） */
        .tabs {{display:flex; justify-content:center; gap:15px; margin: 20px 0;}}
        .tab {{padding: 12px 25px; text-decoration:none; font-weight:bold; border-radius:8px; font-size:1.1em; transition:0.2s; box-shadow: 0 2px 5px rgba(0,0,0,0.5);}}
        .tab-active {{background:#e47911; color:white; border:2px solid #e47911;}}
        .tab-inactive {{background:#333; color:#ccc; border:2px solid #555;}}
        .tab-inactive:hover {{background:#444; color:white; border-color:#777;}}

        .toc {{background: #333; padding: 15px; margin: 0 auto 40px; border-radius: 8px; display: inline-block; position: sticky; top: 10px; z-index: 100; box-shadow: 0 4px 10px rgba(0,0,0,0.5);}}
        .toc a {{color: #fff; text-decoration: none; margin: 0 5px; background: #555; padding: 6px 12px; border-radius: 20px; transition: 0.2s; font-size: 0.9em; display: inline-block;}}
        .toc a:hover {{background: #e47911;}}
        
        h2 {{margin-top: 20px; padding-bottom: 10px; display: inline-block; border-bottom: 2px solid #555; color: #f9f9f9;}}
        .divider {{border: 0; height: 1px; background: #333; margin: 50px 0;}}
        
        .gallery {{display: flex; flex-wrap: wrap; gap: 15px; justify-content: center; margin-top: 20px; padding: 0 10px;}}
        .card {{position: relative; background: #fff; padding: 8px; border-radius: 8px; transition: transform 0.2s;}}
        .card:hover {{transform: scale(1.15); z-index: 10; box-shadow: 0 10px 25px rgba(0,0,0,0.8); cursor: crosshair;}}
        .card img {{width: 140px; height: 140px; object-fit: contain; background: #fff; border-radius: 4px; display: block;}}
        .rank {{position: absolute; top: -8px; left: -8px; background: #e47911; color: #fff; padding: 4px 12px; font-weight: bold; font-size: 14px; border-radius: 4px; box-shadow: 2px 2px 5px rgba(0,0,0,0.4); z-index: 2;}}
    </style></head><body>
    <div class="header-area">
        <a href="../../index.html" class="home-link">← ダッシュボードに戻る</a>
        <h1>Amazon Thumbnail Board ({date_str})</h1>
        
        <div class="tabs">
            <a href="index.html" class="tab tab-inactive">📊 LP詳細レポート (Top 10)</a>
            <a href="thumbnail_board.html" class="tab tab-active">📸 サムネイル一覧 (Top 50)</a>
        </div>
    </div>
    {toc_html}
    """
    
    for cat in all_data:
        html += f'<h2 id="{cat["folder"]}">👑 {cat["name"]} (Top 50)</h2><div class="gallery">\n'
        for r in cat["items"]:
            main_path = f"{cat['folder']}/{r['main']}"
            html += f'<div class="card"><div class="rank">{r["rank"]}</div><img src="{main_path}" loading="lazy" title="{r["title"]}"></div>\n'
        html += '</div><hr class="divider">\n'

    html += "</body></html>"
    with open(os.path.join(save_dir, "thumbnail_board.html"), "w", encoding="utf-8") as f: f.write(html)

# --- スクレイピング本体 ---
def run_scraper():
    today_str = datetime.now().strftime('%Y-%m-%d')
    daily_root_dir = os.path.join(ARCHIVE_ROOT, today_str)
    if not os.path.exists(daily_root_dir): os.makedirs(daily_root_dir)
    
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(user_data_dir=USER_DATA_DIR, headless=False, channel="chrome", viewport={"width": 1280, "height": 900}, user_agent="Mozilla/5.0")
        page = browser.pages[0]
        
        print("\n" + "="*60 + f"\n🚀 究極統合版スクレイピング開始 (全8カテゴリ)\n" + "="*60)
        
        all_categories_data = []
        for idx, target in enumerate(TARGETS):
            print(f"\n[{idx+1}/{len(TARGETS)}] カテゴリ: {target['name']} をスキャン中...")
            try: page.goto(target['url'], wait_until="domcontentloaded")
            except: pass

            # 手動確認
            retry = 0
            while retry < 2:
                if len(page.query_selector_all(".p13n-sc-unpb-faceout, #gridItemRoot, div[id^='p13n-asin-index']")) > 0: break
                print("⚠️ ロボット確認画面が出ていたら手動でクリアして、エンターを押してください。")
                input(">> ")
                retry += 1
            
            # トップ50まで画像を読み込ませるためのスクロール
            print("  -> スクロールして隠れた画像を読み込み中...")
            for _ in range(6):
                page.mouse.wheel(0, 1000)
                time.sleep(0.5)

            items_els = page.query_selector_all(".p13n-sc-unpb-faceout, div[id^='p13n-asin-index']")
            if len(items_els) == 0:
                print(f"❌ スキップします: {target['name']}")
                continue
            
            # 最大50件取得
            items_els = items_els[:50]
            print(f"  -> {len(items_els)}件の基本情報をメモしています...")
            
            cat_dir = os.path.join(daily_root_dir, target['folder'])
            if not os.path.exists(cat_dir): os.makedirs(cat_dir)
            
            cat_items = []
            for i, item in enumerate(items_els):
                try:
                    rank = i + 1
                    link = item.query_selector("a.a-link-normal") or item.query_selector("a")
                    if not link: continue
                    url_part = link.get_attribute("href")
                    full_url = "https://www.amazon.co.jp" + url_part if not url_part.startswith("http") else url_part
                    
                    title = "Item"
                    t1 = item.query_selector(".p13n-sc-truncate-desktop-type2") or item.query_selector("div[class*='truncate']")
                    if t1: title = t1.inner_text().strip()
                    else:
                        img_tag = item.query_selector("img")
                        if img_tag and img_tag.get_attribute("alt"): title = img_tag.get_attribute("alt")

                    img_el = item.query_selector("img")
                    img_src = img_el.get_attribute("src") if img_el else ""
                    
                    # 1. メイン画像の保存（サムネイルボード用・トップ50すべて）
                    main_img_name = f"rank{rank:02d}_main.jpg"
                    save_image(img_src, os.path.join(cat_dir, main_img_name))
                    
                    # 2. サブ画像の取得（詳細レポート用・トップ10のみ）
                    subs = []
                    if rank <= 10:
                        try:
                            p2 = browser.new_page()
                            p2.goto(full_url, wait_until="domcontentloaded")
                            time.sleep(1.5)
                            for j, img in enumerate(p2.query_selector_all("#altImages li.item.imageThumbnail img")[1:7]):
                                src = img.get_attribute("src")
                                if src:
                                    s_name = f"rank{rank:02d}_{j+2:02d}.jpg"
                                    if save_image(src, os.path.join(cat_dir, s_name)): subs.append(s_name)
                            p2.close()
                            print(f"    - {rank}位 LP詳細完了", end="\r")
                        except: 
                            if not p2.is_closed(): p2.close()
                        time.sleep(random.uniform(1.5, 3)) # BAN対策

                    cat_items.append({
                        "rank": rank, "title": title, "url": full_url, 
                        "main": main_img_name, "subs": subs
                    })
                except: continue

            print("")
            all_categories_data.append({"name": target['name'], "folder": target['folder'], "items": cat_items})
            time.sleep(2)

        # 2つのHTMLとダッシュボードを生成！
        generate_detail_html(all_categories_data, daily_root_dir, today_str)
        generate_thumbnail_html(all_categories_data, daily_root_dir, today_str)
        update_root_index()
        
        print(f"\n🎉 全行程完了！ git push してください。")
        browser.close()

if __name__ == "__main__":
    run_scraper()