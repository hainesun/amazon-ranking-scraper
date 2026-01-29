import os
import requests
from playwright.sync_api import sync_playwright

SAVE_DIR = "amazon_data"
TARGET_URL = "https://www.amazon.co.jp/gp/bestsellers/kitchen/"

def save_image(url, path):
    try:
        high_res_url = url.split("._")[0] + ".jpg"
        res = requests.get(high_res_url, timeout=15)
        if res.status_code == 200:
            with open(path, 'wb') as f:
                f.write(res.content)
    except:
        pass

def run_scraper():
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 言語(ja-JP)とロケール(ja-JP)を指定して「日本からのアクセス」を装う
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            locale="ja-JP",
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()

        # タイムアウトを60秒に延長し、読み込み完了条件を緩くする
        page.set_default_timeout(60000)
        
        print("ランキング取得開始...")
        try:
            # 'networkidle' ではなく 'domcontentloaded' (HTML読み込み完了) に変更
            page.goto(TARGET_URL, wait_until="domcontentloaded")
            # 少し待機してJavaScriptの動作を待つ
            page.wait_for_timeout(5000) 
        except Exception as e:
            print(f"ページ読み込みでエラーが発生しましたが、続行を試みます: {e}")

        # 商品リストの取得
        items = page.query_selector_all(".p13n-sc-unpb-faceout")[:10]
        
        # アイテムが取れなかった場合、別のセレクタを試す（AmazonはA/Bテストで構造が変わるため）
        if not items:
            items = page.query_selector_all("[data-asin]")[:10]

        product_links = []
        for i, item in enumerate(items):
            rank = i + 1
            # タイトルやリンクのセレクタを少し柔軟にする
            title_el = item.query_selector("span, div") # より広いタグで探す
            link_el = item.query_selector("a")
            
            if link_el:
                title = f"product_{rank}" # 取得失敗時用のデフォルト名
                if title_el:
                    title = title_el.inner_text().replace("/", "-")[:15].strip()
                
                url = link_el.get_attribute("href")
                if url and url.startswith("/"):
                    url = "https://www.amazon.co.jp" + url
                
                product_links.append({"rank": rank, "title": title, "url": url})
                img_el = item.query_selector("img")
                if img_el:
                    save_image(img_el.get_attribute("src"), os.path.join(SAVE_DIR, f"{rank:02d}_MAIN.jpg"))

        # 詳細ページ解析（上位5件）
        for p_info in product_links[:5]:
            if not p_info['url']: continue
            print(f"解析中: {p_info['rank']}位")
            try:
                page.goto(p_info['url'], wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)
                
                # サブ画像
                thumbs = page.query_selector_all("#altImages .a-spacing-smallitem")
                for j, thumb in enumerate(thumbs[:7]):
                    thumb.hover()
                    page.wait_for_timeout(800)
                    large_img = page.query_selector("#landingImage, #imgTagWrapperId img")
                    if large_img:
                        img_url = large_img.get_attribute("src")
                        save_image(img_url, os.path.join(SAVE_DIR, f"{p_info['rank']:02d}_SUB_{j}.jpg"))
            except:
                print(f"{p_info['rank']}位の個別ページでタイムアウトしました。")

        browser.close()

if __name__ == "__main__":
    run_scraper()