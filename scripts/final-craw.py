# coding: utf-8
"""Vuadocau.com Scraper - Compact nhưng giữ nguyên logic"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time, re, json
from datetime import datetime
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

# ===== CONFIG =====
BASE_URL = "https://vuadocau.com/shop/"
OUTPUT_FILE = f"vuadocau_ALL_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
WAIT = 15

print("VUADOCAU.COM SCRAPER - Bat dau...")

# ===== SETUP =====
options = Options()
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-blink-features=AutomationControlled")
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, WAIT)


# ===== HELPERS =====
def clean_excel(val):
    return ILLEGAL_CHARACTERS_RE.sub("", val) if isinstance(val, str) else val


def safe_text(by, sel):
    try:
        return driver.find_element(by, sel).text.strip()
    except:
        return None


# ===== SCRAPING FUNCTIONS =====
def get_image_url():
    try:
        img = driver.find_element(By.CSS_SELECTOR, "img.wp-post-image")
        return img.get_attribute("src") or img.get_attribute("data-src")
    except:
        try:
            img = driver.find_element(By.CSS_SELECTOR, "figure.woocommerce-product-gallery__wrapper img")
            return img.get_attribute("src") or img.get_attribute("data-src")
        except:
            return None


def get_rating():
    rating_score = count_rate = None
    try:
        star = driver.find_element(By.CSS_SELECTOR, "div.star-rating")
        m = re.search(r"([\d.]+)", star.get_attribute("aria-label") or "")
        if m: rating_score = m.group(1)
    except:
        pass
    try:
        link = driver.find_element(By.CSS_SELECTOR, "a.woocommerce-review-link")
        m = re.search(r"(\d+)", link.text)
        if m: count_rate = m.group(1)
    except:
        pass
    return rating_score, count_rate


def get_first_comment():
    try:
        return driver.find_element(By.CSS_SELECTOR, "ol.commentlist li.review:first-child p").text.strip()
    except:
        return None


def get_sold_count():
    try:
        for pattern in [r'(\d+)\s*đã\s*bán', r'sold[:\s]*(\d+)']:
            matches = re.findall(pattern, driver.page_source, re.IGNORECASE)
            if matches: return matches[0]
        els = driver.find_elements(By.XPATH, "//*[contains(translate(text(),'ĐÃ','đã'),'đã bán')]")
        for el in els:
            m = re.search(r"(\d+)\s*đã\s*bán", el.text)
            if m: return m.group(1)
    except:
        pass
    return None


def get_size_price_raw():
    size_price = {}

    # Variable Product
    try:
        form = driver.find_element(By.CSS_SELECTOR, "form.variations_form")
        data = form.get_attribute("data-product_variations")
        if data:
            variations = json.loads(data)
            for v in variations:
                if not v.get("is_purchasable", True): continue
                attrs = v.get("attributes", {})
                price_raw = v.get("display_price") or v.get("price")
                if price_raw is None: continue

                size = None
                for key, val in attrs.items():
                    if any(kw in key.lower() for kw in ["size", "kich", "chieu", "dai", "length"]):
                        size = str(val).strip()
                        break
                if not size and attrs: size = str(list(attrs.values())[0]).strip()

                if size and size not in size_price:
                    price_val = float(price_raw)
                    size_price[size] = str(int(price_val)) if price_val == int(price_val) else str(price_val)
    except:
        pass

    # Simple Product
    if not size_price:
        try:
            for sel in ["p.price .woocommerce-Price-amount bdi", "p.price .woocommerce-Price-amount",
                        "p.price .amount bdi", "p.price .amount", "span.woocommerce-Price-amount bdi",
                        "span.woocommerce-Price-amount", ".price bdi", ".price .amount",
                        "p.price ins .amount", "p.price span.amount"]:
                try:
                    price_text = driver.find_element(By.CSS_SELECTOR, sel).text.strip()
                    if price_text:
                        price_clean = re.sub(r'[^\d]', '', price_text)
                        if price_clean and int(price_clean) > 0: return None, price_clean
                except:
                    continue

            # Fallback
            for match in re.findall(r'([\d,\.]+)\s*VN[DĐ]', driver.page_source):
                price_clean = re.sub(r'[^\d]', '', match)
                if price_clean and int(price_clean) > 1000: return None, price_clean
        except:
            pass

    if not size_price: return None, None

    # Sort
    try:
        sorted_items = sorted(size_price.items(),
                              key=lambda x: float(re.findall(r'[\d.]+', x[0])[0] or 0))
        size_price = dict(sorted_items)
    except:
        pass

    return " | ".join(size_price.keys()), " | ".join(size_price.values())


def get_color_group():
    colors = []

    # CÁCH 1: Swatches/variations UI
    try:
        for selector in ["ul.variable-items-wrapper span.variable-item-span",
                         "div.variations select[name*='color'] option",
                         "div.variations select[name*='mau'] option",
                         "ul.color-variable-wrapper li",
                         ".tawcvs-swatches .swatch-item-wrapper",
                         ".variations td.value .select-wrapper option"]:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                txt = el.text.strip()
                title = el.get_attribute("title") or el.get_attribute("data-value") or ""
                value = el.get_attribute("value") or ""
                color_text = txt or title or value
                if color_text and color_text.lower() not in ["choose an option", "chọn một tùy chọn", "chọn", ""]:
                    colors.append(color_text)
            if colors: break
    except:
        pass

    # CÁCH 2: Variations data
    if not colors:
        try:
            form = driver.find_element(By.CSS_SELECTOR, "form.variations_form")
            data = form.get_attribute("data-product_variations")
            if data:
                for v in json.loads(data):
                    for key, val in v.get("attributes", {}).items():
                        if any(x in key.lower() for x in ["color", "mau", "colour", "nhom", "group"]):
                            if val and str(val).strip(): colors.append(str(val).strip())
        except:
            pass

    # CÁCH 3: Description text
    if not colors:
        try:
            desc = driver.find_element(By.CSS_SELECTOR, "div.woocommerce-product-details__short-description").text
            m = re.search(r'[Mm]àu\s*sắc\s*[:\-]\s*([^\n.]+)', desc)
            if m: colors = [c.strip() for c in re.split(r'[,;–\-/]', m.group(1)) if c.strip()]
        except:
            pass

    # CÁCH 4: GP-XXX pattern
    if not colors:
        try:
            gps = sorted(set(g.upper() for g in re.findall(r'GP-\d+', driver.page_source, re.IGNORECASE)))
            if gps:
                nums = [int(g.split("-")[1]) for g in gps]
                if len(nums) > 2 and max(nums) - min(nums) == len(nums) - 1:
                    return f"GP-{min(nums)} ~ GP-{max(nums)}"
                return " | ".join(gps)
        except:
            pass

    # CÁCH 5: Product title
    if not colors:
        try:
            title = driver.find_element(By.TAG_NAME, "h1").text
            m = re.search(r'[\(\[\-\s]+(GP-\d+)', title, re.IGNORECASE)
            if m: return m.group(1).upper()
        except:
            pass

    return " | ".join(dict.fromkeys(colors)) if colors else None


# ===== MAIN =====
print(f"Thoi gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Output: {OUTPUT_FILE}\n")

# BUOC 1: Lay links
print("BUOC 1: Lay danh sach san pham...\n")
driver.get(BASE_URL)
product_links_set = set()
page_num = 1

while True:
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.product")))
        cards = driver.find_elements(By.CSS_SELECTOR, "li.product a.woocommerce-LoopProduct-link")

        count_before = len(product_links_set)
        for c in cards:
            href = c.get_attribute("href")
            if href: product_links_set.add(href)

        print(f"  Trang {page_num}: +{len(product_links_set) - count_before} (Tong: {len(product_links_set)})")

        try:
            driver.find_element(By.CSS_SELECTOR, "a.next.page-numbers").click()
            time.sleep(2)
            page_num += 1
        except:
            print("\nDa het trang!")
            break
    except Exception as e:
        print(f"\nLoi: {e}")
        break

product_links = list(product_links_set)
print(f"\nTONG: {len(product_links)} san pham")
print(f"Uoc tinh: ~{int(len(product_links) * 3 / 60)} phut\n")

# BUOC 2: Cao chi tiet
print("=" * 80)
print("BUOC 2: Cao chi tiet tung san pham...\n")

rows = []
start_time = time.time()
errors = []

for idx, url in enumerate(product_links, start=1):
    try:
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

        # Progress
        if idx % 10 == 0 or idx == len(product_links):
            elapsed = time.time() - start_time
            remaining = elapsed / idx * (len(product_links) - idx)
            percent = idx / len(product_links) * 100
            bar = '█' * int(40 * idx / len(product_links)) + '░' * (40 - int(40 * idx / len(product_links)))
            print(f"[{idx}/{len(product_links)}] [{bar}] {percent:.1f}% "
                  f"{int(elapsed / 60)}p{int(elapsed % 60)}s (Con ~{int(remaining / 60)}p)")

        rows.append({
            "name": name, "size": size, "price": price, "color": color,
            "rating_score": rating_score, "count_rate": count_rate,
            "sold_count": sold_count, "first_comment": first_comment,
            "short_description": short_desc, "product_url": url, "image_url": image_url
        })
    except Exception as e:
        errors.append({"url": url, "error": str(e)})
        if idx % 10 == 0: print(f"  Loi [{idx}]: {url[:50]}...")
        continue

driver.quit()

# BUOC 3: Xuat Excel
total_time = time.time() - start_time
minutes, seconds = int(total_time // 60), int(total_time % 60)

if rows:
    print(f"\n{'=' * 80}")
    print("BUOC 3: Xuat du lieu...\n")

    df = pd.DataFrame(rows)
    df = df.map(clean_excel)

    for col in ["rating_score", "count_rate", "sold_count", "first_comment"]:
        if col in df.columns:
            df[col] = df[col].astype(str).replace('None', '').replace('nan', '')

    df.to_excel(OUTPUT_FILE, index=False)

    # Thong ke
    print(f"{'=' * 80}")
    print(f"HOAN THANH!")
    print(f"{'=' * 80}")
    print(f"Thong ke:")
    print(f"  - Tong san pham: {len(df)}/{len(product_links)}")
    print(f"  - Co price: {df['price'].notna().sum()} ({df['price'].notna().sum() / len(df) * 100:.1f}%)")
    print(f"  - Co size: {df['size'].notna().sum()} ({df['size'].notna().sum() / len(df) * 100:.1f}%)")
    print(f"  - Co color: {df['color'].notna().sum()} ({df['color'].notna().sum() / len(df) * 100:.1f}%)")
    print(f"  - Co rating: {df['rating_score'].str.len().gt(0).sum()}")
    print(f"  - Co da ban: {df['sold_count'].str.len().gt(0).sum()}")
    print(f"  - Loi: {len(errors)}")
    print(f"\nThoi gian: {minutes} phut {seconds} giay")
    print(f"File: {OUTPUT_FILE}")
    print(f"{'=' * 80}\n")

    print("PREVIEW 5 SAN PHAM:")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_colwidth', 35)
    print(df[['name', 'price', 'size', 'color']].head().to_string(index=False))

    if errors:
        print(f"\nCo {len(errors)} loi (5 dau):")
        for err in errors[:5]: print(f"  - {err['url'][:55]}...")

    print(f"\n{'=' * 80}")
    print(f"HOAN TAT! Mo file de xem {len(df)} san pham!")
    print(f"{'=' * 80}")
else:
    print("\nKhong co du lieu!")