import os
import time
import requests
from playwright.sync_api import sync_playwright

# --- 設定 ---
TARGET_URL = "https://www.amazon.co.jp/gp/bestsellers/kitchen/" # キッチン用品の例
SAVE_DIR = "amazon_data"

def save_image(url, path):
    """画像を保存するヘルパー関数"""
    try:
        # Amazonの画像URLをリサイズ（解像度を上げる）
        # URL中の ._AC_SR160,160_ のような部分を削除すると高画質になる
        high_res_url = url.split("._")[0] + ".jpg"
        response = requests.get(high_res_url, stream=True)
        if response.status_code == 200:
            with open(path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
    except Exception as e:
        print(f"画像保存失敗: {e}")

def run_scraper():
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)

    with sync_playwright() as p:
        # ブラウザ起動（headless=Falseで動きを確認できます）
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("ランキングページを取得中...")
        page.goto(TARGET_URL)
        page.wait_for_timeout(3000) # 読み込み待ち

        # 1. 商品リストを取得（上位10件）
        items = page.query_selector_all(".p13n-sc-unpb-faceout")[:10]
        product_links = []

        for i, item in enumerate(items):
            rank = i + 1
            # 商品タイトルと詳細URLの取得
            link_el = item.query_selector("a.a-link-normal")
            title_el = item.query_selector(".p13n-sc-truncate-desktop-type2")
            
            if link_el and title_el:
                title = title_el.inner_text().replace("/", "-")[:20] # フォルダ名用に短縮
                url = "https://www.amazon.co.jp" + link_el.get_attribute("href")
                product_links.append({"rank": rank, "title": title, "url": url})

                # メイン画像の保存
                img_el = item.query_selector("img")
                if img_el:
                    img_url = img_el.get_attribute("src")
                    img_name = f"{rank:02d}_MAIN_{title}.jpg"
                    save_image(img_url, os.path.join(SAVE_DIR, img_name))
                    print(f"Saved Main Image: {rank}位")

        # 2. 上位5件の個別ページへ移動してサブ画像（LP）とレビューを取得
        for p_info in product_links[:5]:
            print(f"詳細ページ解析中: {p_info['rank']}位 {p_info['title']}")
            page.goto(p_info['url'])
            page.wait_for_timeout(2000)

            # サブ画像（サムネイル）を順番にホバーして高解像度画像を抜き出す
            thumbs = page.query_selector_all("#altImages .a-spacing-smallitem")
            for j, thumb in enumerate(thumbs[:7]): # 最大7枚程度
                thumb.hover()
                page.wait_for_timeout(500)
                # 中央に表示されたメイン画像要素からURL取得
                large_img = page.query_selector("#landingImage")
                if large_img:
                    img_url = large_img.get_attribute("src")
                    img_name = f"{p_info['rank']:02d}_SUB_{j}_{p_info['title']}.jpg"
                    save_image(img_url, os.path.join(SAVE_DIR, img_name))

            # レビュー（代表的なものを取得）
            review_text = ""
            reviews = page.query_selector_all(".review-text-content span")
            for r in reviews[:3]: # 上位3件
                review_text += r.inner_text() + "\n---\n"
            
            with open(os.path.join(SAVE_DIR, f"{p_info['rank']:02d}_REVIEWS.txt"), "w", encoding="utf-8") as f:
                f.write(review_text)

        print("\n完了しました！ 'amazon_data' フォルダを確認してください。")
        browser.close()

if __name__ == "__main__":
    run_scraper()