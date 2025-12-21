from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import pandas as pd
import time
import re

# ================= CONFIG =================
BASE_URL = "https://vuadocau.com/shop/"
WAIT = 10
LIMIT = 20
OUTPUT_FILE = "vuadocau_test_20_products_FINAL.xlsx"

# ================= DRIVER =================
options = Options()
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)
wait = WebDriverWait(driver, WAIT)

# ================= LOAD SHOP =================
driver.get(BASE_URL)
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.product")))

cards = driver.find_elements(By.CSS_SELECTOR, "li.product")

items = []
has_sale = False

def get_price_from_listing(card):
    try:
        price_box = card.find_element(By.CSS_SELECTOR, "span.price")
        try:
            reg = price_box.find_element(By.CSS_SELECTOR, "del span").text.strip()
            sale = price_box.find_element(By.CSS_SELECTOR, "ins span").text.strip()
        except:
            reg = price_box.text.strip()
            sale = ""
        return reg, sale
    except:
        return "", ""

# ================= COLLECT LINKS + PRICE =================
for card in cards:
    if len(items) >= LIMIT and has_sale:
        break

    try:
        link = card.find_element(
            By.CSS_SELECTOR, "a.woocommerce-LoopProduct-link"
        ).get_attribute("href")

        price_regular, price_sale = get_price_from_listing(card)

        # chỉ lấy sản phẩm có giá
        if not price_regular:
            continue

        if price_sale:
            has_sale = True

        items.append({
            "url": link,
            "price_regular": price_regular,
            "price_sale": price_sale
        })
    except:
        continue

print(f"🔗 Lấy {len(items)} sản phẩm | Có khuyến mãi: {has_sale}")

# ================= SCRAPE DETAIL =================
rows = []

for idx, item in enumerate(items, start=1):
    driver.get(item["url"])
    time.sleep(1.5)

    def safe_text(by, sel):
        try:
            return driver.find_element(by, sel).text.strip()
        except:
            return ""

    page_text = driver.page_source

    # IMAGE
    try:
        img = driver.find_element(By.CSS_SELECTOR, "figure img")
        image_url = img.get_attribute("data-src") or img.get_attribute("src") or ""
    except:
        image_url = ""

    # STOCK STATUS
    stock_status = safe_text(By.CSS_SELECTOR, "p.stock")

    # RATING
    try:
        rating_text = driver.find_element(
            By.CSS_SELECTOR, "div.star-rating"
        ).get_attribute("aria-label")
    except:
        rating_text = ""

    # SOLD COUNT (ĐÃ FIX)
    sold_count = ""
    try:
        sold_text = driver.find_element(
            By.XPATH, "//*[contains(text(),'đã bán')]"
        ).text
        sold_count = re.search(r"\d+", sold_text).group()
    except:
        sold_count = ""

    # SIZE (RAW – chỉ lấy text có thông số, không có thì trống)
    size = ""
    desc = safe_text(By.CSS_SELECTOR, "div.woocommerce-product-details__short-description")
    if desc:
        size_matches = re.findall(r"\d+\s?(?:cm|mm|m|lb|kg|g)", desc.lower()    )
    if size_matches:
        size = " | ".join(sorted(set(size_matches)))


    # COLOR GROUP (RAW – chỉ lấy mã màu thật)
    color_group = ""
    codes = re.findall(r"GP-\d+", page_text, flags=re.IGNORECASE)
    if codes:
        color_group = "~".join(sorted(set(codes)))

    rows.append({
        "name": safe_text(By.TAG_NAME, "h1"),
        "size": size,
        "price_regular": item["price_regular"],
        "price_sale": item["price_sale"],
        "color_group": color_group,
        "image_url": image_url,
        "stock_status": stock_status,
        "sold_count": sold_count,
        "comment_count": len(driver.find_elements(By.CSS_SELECTOR, "ol.commentlist li.review")),
        "rating_text": rating_text,
        "short_description": desc,
        "product_url": item["url"]
    })

# ================= EXPORT =================
df = pd.DataFrame(rows)
df.to_excel(OUTPUT_FILE, index=False)

driver.quit()

print(f"\n✅ HOÀN THÀNH – file xuất ra: {OUTPUT_FILE}")
