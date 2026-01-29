import os
import requests
from playwright.sync_api import sync_playwright

# 保存先
SAVE_DIR = "amazon_data"
# 解析したいカテゴリーURL
TARGET_URL = "https://www.amazon.co.jp/gp/bestsellers/kitchen/"

def save_image(url, path):
    try:
        # 高解像度化
        high_res_url = url.split("._")[0] + ".jpg"
        res = requests.get(high_res_url, timeout=10)
        if res.status_code == 200:
            with open(path, 'wb') as f:
                f.write(res.content)
    except:
        pass

def run_scraper():
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)

    with sync_playwright() as p:
        # headless=True（画面表示なし）がGitHub Actionsでは必須
        browser = p.chromium.launch(headless=True)
        # 人間らしく見せるための設定
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("ランキング取得中...")
        page.goto(TARGET_URL, wait_until="networkidle")

        items = page.query_selector_all(".p13n-sc-unpb-faceout")[:10]
        product_links = []

        for i, item in enumerate(items):
            rank = i + 1
            title_el = item.query_selector(".p13n-sc-truncate-desktop-type2")
            link_el = item.query_selector("a.a-link-normal")
            
            if title_el and link_el:
                title = title_el.inner_text().replace("/", "-")[:15]
                url = "https://www.amazon.co.jp" + link_el.get_attribute("href")
                product_links.append({"rank": rank, "title": title, "url": url})

                # メイン画像保存
                img_el = item.query_selector("img")
                if img_el:
                    save_image(img_el.get_attribute("src"), os.path.join(SAVE_DIR, f"{rank:02d}_MAIN.jpg"))

        # 詳細解析（上位5件）
        for p_info in product_links[:5]:
            print(f"詳細解析中: {p_info['rank']}位")
            page.goto(p_info['url'], wait_until="networkidle")
            
            # サブ画像（LP）
            thumbs = page.query_selector_all("#altImages .a-spacing-smallitem")
            for j, thumb in enumerate(thumbs[:7]):
                thumb.hover()
                page.wait_for_timeout(500)
                large_img = page.query_selector("#landingImage")
                if large_img:
                    save_image(large_img.get_attribute("src"), os.path.join(SAVE_DIR, f"{p_info['rank']:02d}_SUB_{j}.jpg"))

            # レビュー取得
            reviews = page.query_selector_all(".review-text-content span")
            review_text = "\n".join([r.inner_text() for r in reviews[:3]])
            with open(os.path.join(SAVE_DIR, f"{p_info['rank']:02d}_REVIEWS.txt"), "w", encoding="utf-8") as f:
                f.write(review_text)

        browser.close()

if __name__ == "__main__":
    run_scraper()