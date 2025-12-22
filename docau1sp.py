from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time, re, json

# ================= CONFIG =================
URLS = [
    "https://vuadocau.com/thung-dung-ca-da-nang-nhieu-kich-co/",
    "https://vuadocau.com/moi-cau-guide-post-bowan-pencil-80s/"
]
OUTPUT_FILE = "vuadocau_test_final.xlsx"

# ================= DRIVER =================
options = Options()
options.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)

# ================= HELPERS =================
def safe_text(by, sel):
    try:
        return driver.find_element(by, sel).text.strip()
    except:
        return ""

def get_image_url():
    try:
        img = driver.find_element(By.CSS_SELECTOR, "img.wp-post-image")
        return img.get_attribute("src") or img.get_attribute("data-src") or ""
    except:
        try:
            img = driver.find_element(
                By.CSS_SELECTOR,
                "figure.woocommerce-product-gallery__wrapper img"
            )
            return img.get_attribute("src") or img.get_attribute("data-src") or ""
        except:
            return ""

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
        review_link = driver.find_element(By.CSS_SELECTOR, "a.woocommerce-review-link")
        m = re.search(r"(\d+)", review_link.text)
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
        return ""


def get_size_price_raw():
    size_price = {}
    try:
        form = driver.find_element(By.CSS_SELECTOR, "form.variations_form")
        data = form.get_attribute("data-product_variations")
        if not data:
            return "", ""

        variations = json.loads(data)
        for v in variations:
            attrs = v.get("attributes", {})
            price = v.get("display_price")

            size = ""
            for k, val in attrs.items():
                if "size" in k or "kich" in k:
                    size = str(val)

            if size and price is not None and size not in size_price:
                size_price[size] = str(int(price))

    except:
        pass

    sizes = " | ".join(size_price.keys())
    prices = " | ".join(size_price.values())
    return sizes, prices

def get_sold_count():
    try:
        els = driver.find_elements(
            By.XPATH,
            "//*[contains(translate(text(),'ĐÃ','đã'),'đã bán')]"
        )
        for el in els:
            text = el.text.strip()
            m = re.search(r"(\d+)\s*đã\s*bán", text)
            if m:
                return m.group(1)
        return ""
    except:
        return ""


def get_color_group():
    colors = []

    # 1️⃣ ƯU TIÊN: màu dạng swatch (ảnh + text)
    try:
        spans = driver.find_elements(
            By.CSS_SELECTOR,
            "ul.variable-items-wrapper span.variable-item-span"
        )
        for s in spans:
            txt = s.text.strip()
            if txt and txt.lower() not in ["chọn một tùy chọn"]:
                colors.append(txt)
    except:
        pass

    if colors:
        return " | ".join(dict.fromkeys(colors))  # giữ thứ tự, bỏ trùng

    # 2️⃣ FALLBACK: GP-xxx nếu không có swatch
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

    return ""


# ================= MAIN =================
rows = []

for idx, url in enumerate(URLS, start=1):
    print(f"📦 Crawl: {url}")
    driver.get(url)
    time.sleep(4)

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
df.to_excel(OUTPUT_FILE, index=False)

driver.quit()
print(f"✅ Hoàn thành – file: {OUTPUT_FILE}")
