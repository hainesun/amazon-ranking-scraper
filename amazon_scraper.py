import os
import time
import random
import requests
import urllib.parse
from datetime import datetime
from playwright.sync_api import sync_playwright

# --- 設定エリア ---
BASE_DIR = "."
ARCHIVE_ROOT = "archives"
USER_DATA_DIR = "./my_browser_data"

# ★ ランキングのターゲット
TARGETS = [
    {"name": "メンズバッグ・財布", "folder": "mens_bag_wallet", "url": "https://www.amazon.co.jp/gp/bestsellers/fashion/2221074051/"},
    {"name": "レディースバッグ", "folder": "ladies_bag", "url": "https://www.amazon.co.jp/gp/bestsellers/fashion/5355945051/"},
    {"name": "レディース財布", "folder": "ladies_wallet", "url": "https://www.amazon.co.jp/gp/bestsellers/fashion/2221186051/"},
    {"name": "収納用品", "folder": "storage", "url": "https://www.amazon.co.jp/gp/bestsellers/kitchen/2491381051/"}
]

# ★ 検索キーワードのターゲット
SEARCH_TARGETS = [
    {"keyword": "名刺入れ レディース", "folder": "search_meishi_ladies"},
    {"keyword": "買い物 amazon", "folder": "search_kaimono_amazon"},
    {"keyword": "めいしいれ レディース 人気", "folder": "search_meishi_ladies_ninki"},
    {"keyword": "財布 レディース", "folder": "search_wallet_ladies"},
    {"keyword": "財布 レディース 2つ折り", "folder": "search_wallet_ladies_bifold"},
    {"keyword": "トートバッグ メンズ", "folder": "search_totebag_mens"},
    {"keyword": "財布 コンパクト", "folder": "search_wallet_compact"},
    {"keyword": "バッグ レディース", "folder": "search_bag_ladies"}
]

# ★★★ 修正ポイント：画像保存を「二段構え」にして確実に取得する ★★★
def save_image(url, path):
    try:
        if not url: return False
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Referer": "https://www.amazon.co.jp/"
        }
        
        # 1. まず「高画質化」を試す
        if "._" in url:
            high_res_url = url.split("._")[0] + ".jpg"
            res = requests.get(high_res_url, headers=headers, timeout=10)
            if res.status_code == 200:
                with open(path, 'wb') as f: f.write(res.content)
                return True

        # 2. 高画質化に失敗した、または特殊なURLの場合は「元のURL」で確実に保存
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            with open(path, 'wb') as f: f.write(res.content)
            return True
            
    except: pass
    return False

def get_date_links(current_date_str):
    if not os.path.exists(ARCHIVE_ROOT): return ""
    dates = sorted([d for d in os.listdir(ARCHIVE_ROOT) if os.path.isdir(os.path.join(ARCHIVE_ROOT, d))], reverse=True)
    html = '<div class="date-nav-bar"><span class="nav-label">📅 履歴:</span> '
    for d in dates:
        if d == current_date_str: html += f'<span class="nav-current">{d}</span> '
        else: html += f'<a href="../{d}/index.html" class="nav-link">{d}</a> '
    html += '</div>'
    return html

def update_root_index():
    if not os.path.exists(ARCHIVE_ROOT): return
    dates = sorted([d for d in os.listdir(ARCHIVE_ROOT) if os.path.isdir(os.path.join(ARCHIVE_ROOT, d))], reverse=True)
    links_html = "".join([f'<a href="{ARCHIVE_ROOT}/{d}/index.html" class="date-card"><span class="icon">📁</span><span class="date-text">{d}</span><span class="arrow">→</span></a>' for d in dates])
    html = f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Amazon LP Dashboard</title><style>body {{ font-family: -apple-system, sans-serif; background-color: #f0f2f5; color: #333; padding: 20px; }}.container {{ max-width: 800px; margin: 0 auto; }}header {{ text-align: center; margin-bottom: 40px; padding: 20px 0; }}h1 {{ color: #232f3e; margin: 0; }}.dashboard-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; }}.date-card {{ display: flex; align-items: center; justify-content: space-between; background: white; padding: 20px; border-radius: 12px; text-decoration: none; color: #333; box-shadow: 0 2px 5px rgba(0,0,0,0.05); transition: 0.2s; border-left: 5px solid #e47911; }}.date-card:hover {{ transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}</style></head><body><div class="container"><header><h1>Amazon LP Research Dashboard</h1><p>収集したランキング・検索結果のアーカイブ一覧</p></header><div class="dashboard-grid">{links_html}</div></div></body></html>"""
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

def generate_tabs(active_tab):
    tabs = [
        ("index.html", "📊 ランキング LP詳細 (Top10)", "detail"),
        ("thumbnail_board.html", "📸 ランキング サムネイル (Top50)", "rank_thumb"),
        ("search_board.html", "🔍 検索結果 サムネイル (SEO順)", "search_thumb")
    ]
    html = '<div class="tabs">'
    for link, name, id in tabs:
        active_class = "tab-active" if active_tab == id else "tab-inactive"
        html += f'<a href="{link}" class="tab {active_class}">{name}</a>'
    html += '</div>'
    return html

# --- ① ランキング詳細レポート ---
def generate_detail_html(all_data, save_dir, date_str):
    date_nav_html = get_date_links(date_str)
    tabs_html = generate_tabs("detail")
    toc_html = '<div class="toc"><strong>📂 カテゴリ:</strong> ' + "".join([f'<a href="#{c["folder"]}">{c["name"]}</a> ' for c in all_data]) + '</div>'

    html = f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><title>LP Report {date_str}</title>
    <style>
        body{{font-family:-apple-system,sans-serif;background:#f4f4f4;padding:20px;color:#333;margin:0;}}
        .container {{max-width: 1400px; margin: 0 auto;}}
        .header-area {{text-align:center; margin-bottom:20px;}}
        h1 {{color:#232f3e; margin:0; font-size:24px;}}
        .home-link {{display:inline-block; margin-top:5px; color:#007185; text-decoration:none;}}
        .tabs {{display:flex; justify-content:center; gap:10px; margin: 20px 0; flex-wrap:wrap;}}
        .tab {{padding: 10px 20px; text-decoration:none; font-weight:bold; border-radius:8px; font-size:1em; transition:0.2s; box-shadow: 0 2px 5px rgba(0,0,0,0.1);}}
        .tab-active {{background:#e47911; color:white; border:2px solid #e47911;}}
        .tab-inactive {{background:white; color:#333; border:2px solid #ddd;}}
        .tab-inactive:hover {{background:#f0f2f5; border-color:#aaa;}}
        .date-nav-bar {{background:white; padding:10px; margin-bottom:15px; border-radius:8px; text-align:center; font-size:0.9em;}}
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
            {tabs_html}
        </div>
        {toc_html}
    """
    for cat in all_data:
        html += f'<div id="{cat["folder"]}" class="category-section"><h2 class="cat-title">📦 {cat["name"]} (Top 10)</h2><table><thead><tr><th style="width:50px;">Rank</th><th style="width:130px;">Thumb</th><th style="width:220px;">Product Info</th><th>LP Gallery</th></tr></thead><tbody>'
        for r in cat["items"][:10]:
            main_path = f"{cat['folder']}/{r['main']}"
            subs_html = "".join([f'<img src="{cat["folder"]}/{s}" class="lp-thumb" onclick="openModal(this.src)">' for s in r['subs']])
            if not subs_html: subs_html = '<span style="color:#ccc; font-size:0.8em">LP画像なし</span>'
            title = r['title'] if r['title'] and r['title'] != "Item 1" else "商品タイトル取得不可"
            html += f'<tr><td class="col-rank">{r["rank"]}</td><td class="col-main"><img src="{main_path}" class="main-img" onclick="openModal(this.src)"></td><td class="col-info"><a href="{r["url"]}" target="_blank" class="product-title">{title}</a><div style="margin-top:8px;"><a href="{r["url"]}" target="_blank" style="font-size:0.85em; color:#555; text-decoration:none;">🔗 Amazonで見る</a></div></td><td class="col-lp"><div class="lp-gallery">{subs_html}</div></td></tr>'
        html += "</tbody></table></div>"
    html += """</div><div id="imageModal" class="modal" onclick="closeModal()"><span class="close">&times;</span><img class="modal-content" id="modalImg"></div><script>function openModal(src) { document.getElementById("imageModal").style.display = "block"; document.getElementById("modalImg").src = src; document.body.style.overflow = "hidden"; } function closeModal() { document.getElementById("imageModal").style.display = "none"; document.body.style.overflow = "auto"; } document.addEventListener('keydown', function(event) { if (event.key === "Escape") closeModal(); });</script></body></html>"""
    with open(os.path.join(save_dir, "index.html"), "w", encoding="utf-8") as f: f.write(html)

# --- ② ギャラリー共通生成関数（ランキング用＆検索用） ---
def generate_gallery_html(all_data, save_dir, date_str, filename, title, tab_id):
    tabs_html = generate_tabs(tab_id)
    toc_html = '<div class="toc"><strong>📂 カテゴリ:</strong> ' + "".join([f'<a href="#{c["folder"]}">{c["name"]}</a> ' for c in all_data]) + '</div>'
    
    # 検索SEO順の場合はアイコンを変える
    rank_icon = "🔍" if "search" in tab_id else "👑"

    html = f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><title>{title} {date_str}</title>
    <style>
        body {{background: #1a1a1a; color: #fff; font-family: -apple-system, sans-serif; padding: 20px; text-align: center; margin: 0;}}
        .header-area {{margin-bottom: 20px;}}
        h1 {{color: #e47911; margin: 0; font-size: 24px;}}
        .home-link {{display:inline-block; margin-top:5px; color:#4db8ff; text-decoration:none;}}
        .tabs {{display:flex; justify-content:center; gap:10px; margin: 20px 0; flex-wrap:wrap;}}
        .tab {{padding: 10px 20px; text-decoration:none; font-weight:bold; border-radius:8px; font-size:1em; transition:0.2s; box-shadow: 0 2px 5px rgba(0,0,0,0.5);}}
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
        .error-msg {{color: #ff6b6b; font-size: 12px; padding: 20px;}}
    </style></head><body>
    <div class="header-area">
        <a href="../../index.html" class="home-link">← ダッシュボードに戻る</a>
        <h1>{title} ({date_str})</h1>
        {tabs_html}
    </div>
    {toc_html}
    """
    for cat in all_data:
        html += f'<h2 id="{cat["folder"]}">{rank_icon} {cat["name"]}</h2><div class="gallery">\n'
        
        # 画像が1枚もない場合のエラーハンドリング
        if not cat["items"]:
            html += '<div class="error-msg">※このキーワードの検索結果、または画像の取得に失敗しました</div>'
            
        for r in cat["items"]:
            main_path = f"{cat['folder']}/{r['main']}"
            html += f'<div class="card"><div class="rank">{r["rank"]}</div><img src="{main_path}" loading="lazy" title="{r["title"]}"></div>\n'
        html += '</div><hr class="divider">\n'
    html += "</body></html>"
    with open(os.path.join(save_dir, filename), "w", encoding="utf-8") as f: f.write(html)

# --- スクレイピング本体 ---
def run_scraper():
    today_str = datetime.now().strftime('%Y-%m-%d')
    daily_root_dir = os.path.join(ARCHIVE_ROOT, today_str)
    if not os.path.exists(daily_root_dir): os.makedirs(daily_root_dir)
    
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(user_data_dir=USER_DATA_DIR, headless=False, channel="chrome", viewport={"width": 1280, "height": 900}, user_agent="Mozilla/5.0")
        page = browser.pages[0]
        
        # ---------------------------------------------------------
        # Part 1: ランキングデータの取得
        # ---------------------------------------------------------
        print("\n" + "="*60 + f"\n🚀 【1/2】ランキングデータ収集開始\n" + "="*60)
        rank_data = []
        for idx, target in enumerate(TARGETS):
            print(f"\n[{idx+1}/{len(TARGETS)}] ランキング: {target['name']} をスキャン中...")
            try: page.goto(target['url'], wait_until="domcontentloaded")
            except: pass

            retry = 0
            while retry < 2:
                if len(page.query_selector_all(".p13n-sc-unpb-faceout, #gridItemRoot, div[id^='p13n-asin-index']")) > 0: break
                print("⚠️ 手動でロボット確認をクリアし、エンターを押してください。")
                input(">> ")
                retry += 1
            
            for _ in range(6): page.mouse.wheel(0, 1000); time.sleep(0.5)

            items_els = page.query_selector_all(".p13n-sc-unpb-faceout, div[id^='p13n-asin-index']")
            if len(items_els) == 0: continue
            
            items_els = items_els[:50]
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
                    
                    main_img_name = f"rank{rank:02d}_main.jpg"
                    if save_image(img_src, os.path.join(cat_dir, main_img_name)):
                        # メイン画像の保存に成功した場合のみリストに追加
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
                                print(f"    - ランキング {rank}位 LP詳細完了", end="\r")
                            except: 
                                if not p2.is_closed(): p2.close()
                            time.sleep(random.uniform(1.0, 2.0))

                        cat_items.append({"rank": rank, "title": title, "url": full_url, "main": main_img_name, "subs": subs})
                except: continue

            print("")
            rank_data.append({"name": target['name'], "folder": target['folder'], "items": cat_items})
            time.sleep(2)

        # ---------------------------------------------------------
        # Part 2: 検索結果データの取得（SEO順）
        # ---------------------------------------------------------
        print("\n" + "="*60 + f"\n🚀 【2/2】検索キーワード(SEO順) データ収集開始\n" + "="*60)
        search_data = []
        for idx, target in enumerate(SEARCH_TARGETS):
            kw = target['keyword']
            print(f"\n[{idx+1}/{len(SEARCH_TARGETS)}] 検索KW: 「{kw}」 をスキャン中...")
            
            search_url = f"https://www.amazon.co.jp/s?k={urllib.parse.quote(kw)}"
            try: page.goto(search_url, wait_until="domcontentloaded")
            except: pass

            retry = 0
            while retry < 2:
                # 検索結果の要素セレクタ
                if len(page.query_selector_all("div[data-component-type='s-search-result']")) > 0: break
                print("⚠️ 手動でロボット確認をクリアし、エンターを押してください。")
                input(">> ")
                retry += 1

            for _ in range(8): page.mouse.wheel(0, 1000); time.sleep(0.5)

            items_els = page.query_selector_all("div[data-component-type='s-search-result']")
            if len(items_els) == 0: continue
            
            # 自然検索のトップ50
            items_els = items_els[:50]
            cat_dir = os.path.join(daily_root_dir, target['folder'])
            if not os.path.exists(cat_dir): os.makedirs(cat_dir)
            
            cat_items = []
            for i, item in enumerate(items_els):
                try:
                    rank = i + 1
                    link = item.query_selector("h2 a") or item.query_selector("a.a-link-normal")
                    if not link: continue
                    url_part = link.get_attribute("href")
                    full_url = "https://www.amazon.co.jp" + url_part if not url_part.startswith("http") else url_part
                    
                    title_el = item.query_selector("h2 span") or item.query_selector("h2")
                    title = title_el.inner_text().strip() if title_el else f"Search Item {rank}"
                    
                    img_el = item.query_selector("img.s-image")
                    img_src = img_el.get_attribute("src") if img_el else ""
                    
                    main_img_name = f"seo{rank:02d}_main.jpg"
                    
                    # ★ここで画像の保存に成功した要素だけをリストに追加する
                    if save_image(img_src, os.path.join(cat_dir, main_img_name)):
                        cat_items.append({"rank": rank, "title": title, "url": full_url, "main": main_img_name, "subs": []})
                        print(f"    - SEO {rank}位 画像取得完了", end="\r")
                except: continue
            
            print("")
            search_data.append({"name": kw, "folder": target['folder'], "items": cat_items})
            time.sleep(2)

        # 全てのHTMLファイルを生成！
        generate_detail_html(rank_data, daily_root_dir, today_str)
        generate_gallery_html(rank_data, daily_root_dir, today_str, "thumbnail_board.html", "Amazon Ranking Thumbnails", "rank_thumb")
        generate_gallery_html(search_data, daily_root_dir, today_str, "search_board.html", "Amazon Search SEO Thumbnails", "search_thumb")
        update_root_index()
        
        print(f"\n🎉 全行程完了！ git push してください。")
        browser.close()

if __name__ == "__main__":
    run_scraper()