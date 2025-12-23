from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time, re, json

from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

# ================= CONFIG =================
BASE_URL = "https://vuadocau.com/shop/"
OUTPUT_FILE = "vuadocau_ALL_products.xlsx"
WAIT = 15

# ================= DRIVER =================
options = Options()
options.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, WAIT)

# ================= CLEAN EXCEL =================
def clean_excel(val):
    if isinstance(val, str):
        return ILLEGAL_CHARACTERS_RE.sub("", val)
    return val

# ================= HELPERS =================
def safe_text(by, sel):
    try:
        return driver.find_element(by, sel).text.strip()
    except:
        return None

def get_image_url():
    try:
        img = driver.find_element(By.CSS_SELECTOR, "img.wp-post-image")
        return img.get_attribute("src") or img.get_attribute("data-src")
    except:
        try:
            img = driver.find_element(
                By.CSS_SELECTOR,
                "figure.woocommerce-product-gallery__wrapper img"
            )
            return img.get_attribute("src") or img.get_attribute("data-src")
        except:
            return None

def get_rating():
    rating_score = None
    count_rate = None

    try:
        star = driver.find_element(By.CSS_SELECTOR, "div.star-rating")
        label = star.get_attribute("aria-label") or ""
        m = re.search(r"([\d.]+)", label)
        if m:
            rating_score = m.group(1)
    except:
        pass

    try:
        link = driver.find_element(By.CSS_SELECTOR, "a.woocommerce-review-link")
        m = re.search(r"(\d+)", link.text)
        if m:
            count_rate = m.group(1)
    except:
        pass

    return rating_score, count_rate

def get_first_comment():
    try:
        return driver.find_element(
            By.CSS_SELECTOR,
            "ol.commentlist li.review:first-child p"
        ).text.strip()
    except:
        return None

def get_sold_count():
    try:
        els = driver.find_elements(
            By.XPATH,
            "//*[contains(translate(text(),'ĐÃ','đã'),'đã bán')]"
        )
        for el in els:
            m = re.search(r"(\d+)\s*đã\s*bán", el.text)
            if m:
                return m.group(1)
    except:
        pass
    return None

def get_size_price_raw():
    size_price = {}
    try:
        form = driver.find_element(By.CSS_SELECTOR, "form.variations_form")
        data = form.get_attribute("data-product_variations")
        if not data:
            return None, None

        variations = json.loads(data)
        for v in variations:
            attrs = v.get("attributes", {})
            price = v.get("display_price")

            size = None
            for k, val in attrs.items():
                if "size" in k or "kich" in k:
                    size = str(val)

            if size and price is not None and size not in size_price:
                size_price[size] = str(int(price))

    except:
        pass

    if not size_price:
        return None, None

    return " | ".join(size_price.keys()), " | ".join(size_price.values())

def get_color_group():
    colors = []

    # ƯU TIÊN SWATCH
    try:
        spans = driver.find_elements(
            By.CSS_SELECTOR,
            "ul.variable-items-wrapper span.variable-item-span"
        )
        for s in spans:
            txt = s.text.strip()
            if txt:
                colors.append(txt)
    except:
        pass

    if colors:
        return " | ".join(dict.fromkeys(colors))

    # FALLBACK GP
    try:
        gps = re.findall(r"GP-\d+", driver.page_source, flags=re.IGNORECASE)
        gps = sorted(set(g.upper() for g in gps))
        if gps:
            nums = [int(g.split("-")[1]) for g in gps]
            if max(nums) - min(nums) == len(nums) - 1:
                return f"GP-{min(nums)} ~ GP-{max(nums)}"
            return " | ".join(gps)
    except:
        pass

    return None

# ================= GET ALL PRODUCT LINKS =================
print("🚀 Lấy danh sách sản phẩm...")
driver.get(BASE_URL)
product_links = set()

while True:
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.product")))
    cards = driver.find_elements(By.CSS_SELECTOR, "li.product a.woocommerce-LoopProduct-link")
    for c in cards:
        href = c.get_attribute("href")
        if href:
            product_links.add(href)

    try:
        driver.find_element(By.CSS_SELECTOR, "a.next.page-numbers").click()
        time.sleep(2)
    except:
        break

product_links = list(product_links)
print(f"🔗 Tổng sản phẩm: {len(product_links)}")

# ================= SCRAPE ALL =================
rows = []

for idx, url in enumerate(product_links, start=1):
    print(f"📦 [{idx}/{len(product_links)}] {url}")
    driver.get(url)
    time.sleep(3)

    name = safe_text(By.TAG_NAME, "h1")
    short_desc = safe_text(By.CSS_SELECTOR, "div.woocommerce-product-details__short-description")
    image_url = get_image_url()

    size, price = get_size_price_raw()
    color = get_color_group()
    rating_score, count_rate = get_rating()
    sold_count = get_sold_count()
    first_comment = get_first_comment()

    rows.append({
        "name": name,
        "size": size,
        "price": price,
        "color": color,
        "rating_score": rating_score,
        "count_rate": count_rate,
        "sold_count": sold_count,
        "first_comment": first_comment,
        "short_description": short_desc,
        "product_url": url,
        "image_url": image_url
    })

# ================= EXPORT =================
df = pd.DataFrame(rows)

# Làm sạch ký tự cấm Excel
df = df.applymap(clean_excel)

# Ép kiểu string để không hiện 0
for col in ["rating_score", "count_rate", "sold_count", "first_comment"]:
    df[col] = df[col].astype("string")

df.to_excel(OUTPUT_FILE, index=False)
driver.quit()

print(f"\n✅ HOÀN THÀNH – Đã cào {len(df)} sản phẩm")
print(f"📄 File: {OUTPUT_FILE}")
