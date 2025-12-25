from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time, re, json
from datetime import datetime

from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

# ================= CONFIG =================
BASE_URL = "https://vuadocau.com/shop/"
OUTPUT_FILE = f"vuadocau_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
WAIT = 15

# ================= DRIVER =================
options = Options()
options.add_argument("--window-size=1920,1080")
# options.add_argument("--headless")  # Bỏ comment nếu muốn chạy ẩn
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
        page_text = driver.page_source
        patterns = [
            r'(\d+)\s*đã\s*bán',
            r'sold[:\s]*(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                return matches[0]
        
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
    """Lấy size và price - Hỗ trợ cả variable và simple product"""
    size_price = {}
    
    # CHECK 1: Variable Product (có variations)
    try:
        form = driver.find_element(By.CSS_SELECTOR, "form.variations_form")
        data = form.get_attribute("data-product_variations")
        
        if data:
            variations = json.loads(data)
            
            for v in variations:
                if not v.get("is_purchasable", True):
                    continue
                
                attrs = v.get("attributes", {})
                price_raw = v.get("display_price") or v.get("price")
                
                if price_raw is None:
                    continue
                
                # Tìm size attribute
                size = None
                for key, val in attrs.items():
                    key_lower = key.lower()
                    if any(keyword in key_lower for keyword in [
                        "size", "kich", "chieu", "dai", "length"
                    ]):
                        size = str(val).strip()
                        break
                
                if not size and attrs:
                    size = str(list(attrs.values())[0]).strip()
                
                if size and size not in size_price:
                    price_val = float(price_raw)
                    if price_val == int(price_val):
                        size_price[size] = str(int(price_val))
                    else:
                        size_price[size] = str(price_val)
    except:
        pass
    
    # CHECK 2: Simple Product (giá cố định)
    if not size_price:
        try:
            price_selectors = [
                "p.price .woocommerce-Price-amount bdi",
                "p.price .woocommerce-Price-amount",
                "p.price .amount bdi",
                "p.price .amount",
                "span.woocommerce-Price-amount bdi",
                "span.woocommerce-Price-amount",
                ".price bdi",
                ".price .amount",
                "p.price ins .amount",
                "p.price span.amount",
            ]
            
            for sel in price_selectors:
                try:
                    price_el = driver.find_element(By.CSS_SELECTOR, sel)
                    price_text = price_el.text.strip()
                    
                    if price_text:
                        price_clean = re.sub(r'[^\d]', '', price_text)
                        
                        if price_clean and int(price_clean) > 0:
                            return None, price_clean
                except:
                    continue
            
            # Fallback: Tìm trong page source
            price_matches = re.findall(r'([\d,\.]+)\s*VN[DĐ]', driver.page_source)
            if price_matches:
                for match in price_matches:
                    price_clean = re.sub(r'[^\d]', '', match)
                    if price_clean and int(price_clean) > 1000:
                        return None, price_clean
        except:
            pass
    
    if not size_price:
        return None, None
    
    # Sort sizes
    try:
        def extract_number(s):
            nums = re.findall(r'[\d.]+', s)
            return float(nums[0]) if nums else 0
        
        sorted_items = sorted(size_price.items(), key=lambda x: extract_number(x[0]))
        size_price = dict(sorted_items)
    except:
        pass
    
    sizes = " | ".join(size_price.keys())
    prices = " | ".join(size_price.values())
    
    return sizes, prices

def get_color_group():
    """Lấy màu sắc/nhóm sản phẩm"""
    colors = []
    
    # CÁCH 1: Swatches/variations UI
    try:
        selectors = [
            "ul.variable-items-wrapper span.variable-item-span",
            "div.variations select[name*='color'] option",
            "div.variations select[name*='mau'] option",
            "ul.color-variable-wrapper li",
            ".tawcvs-swatches .swatch-item-wrapper",
            ".variations td.value .select-wrapper option",
        ]
        
        for selector in selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                txt = el.text.strip()
                title = el.get_attribute("title") or el.get_attribute("data-value") or ""
                value = el.get_attribute("value") or ""
                
                color_text = txt or title or value
                if color_text and color_text.lower() not in [
                    "choose an option", "chọn một tùy chọn", "chọn", ""
                ]:
                    colors.append(color_text)
            
            if colors:
                break
    except:
        pass
    
    # CÁCH 2: Variations data trong form
    if not colors:
        try:
            form = driver.find_element(By.CSS_SELECTOR, "form.variations_form")
            data = form.get_attribute("data-product_variations")
            
            if data:
                variations = json.loads(data)
                for v in variations:
                    attrs = v.get("attributes", {})
                    for key, val in attrs.items():
                        key_lower = key.lower()
                        if any(x in key_lower for x in [
                            "color", "mau", "colour", "nhom", "group"
                        ]):
                            if val and str(val).strip():
                                colors.append(str(val).strip())
        except:
            pass
    
    # CÁCH 3: Description text (Pattern: "Màu sắc: xxx")
    if not colors:
        try:
            desc = driver.find_element(
                By.CSS_SELECTOR, 
                "div.woocommerce-product-details__short-description"
            ).text
            
            color_match = re.search(
                r'[Mm]àu\s*sắc\s*[:\-]\s*([^\n.]+)',
                desc
            )
            if color_match:
                color_str = color_match.group(1).strip()
                color_parts = re.split(r'[,;–\-/]', color_str)
                colors = [c.strip() for c in color_parts if c.strip()]
        except:
            pass
    
    # CÁCH 4: GP-XXX pattern (cho mồi câu)
    if not colors:
        try:
            gps = re.findall(r'GP-\d+', driver.page_source, flags=re.IGNORECASE)
            gps = sorted(set(g.upper() for g in gps))
            
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
            gp_match = re.search(r'[\(\[\-\s]+(GP-\d+)', title, re.IGNORECASE)
            if gp_match:
                return gp_match.group(1).upper()
        except:
            pass
    
    if colors:
        unique_colors = list(dict.fromkeys(colors))
        return " | ".join(unique_colors)
    
    return None

# ================= GET ALL PRODUCT LINKS =================
print("🚀 BẮT ĐẦU CÀO DỮ LIỆU VUADOCAU.COM")
print("="*80)
print("📋 BƯỚC 1: Lấy danh sách sản phẩm từ tất cả các trang...\n")

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
            if href:
                product_links_set.add(href)
        
        count_after = len(product_links_set)
        new_products = count_after - count_before
        print(f"  Trang {page_num}: +{new_products} sản phẩm (Tổng: {count_after})")
        
        # Tìm nút Next
        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, "a.next.page-numbers")
            next_btn.click()
            time.sleep(2)
            page_num += 1
        except:
            print("\n✅ Đã hết trang!")
            break
            
    except Exception as e:
        print(f"\n⚠️ Lỗi khi load trang: {e}")
        break

product_links = list(product_links_set)
print(f"\n🔗 TỔNG CỘNG: {len(product_links)} sản phẩm unique")

# ================= SCRAPE ALL PRODUCTS =================
print(f"\n{'='*80}")
print("📦 BƯỚC 2: Cào chi tiết từng sản phẩm...\n")

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
        
        # Progress indicator
        if idx % 10 == 0 or idx == len(product_links):
            elapsed = time.time() - start_time
            avg_time = elapsed / idx
            remaining = avg_time * (len(product_links) - idx)
            
            print(f"📦 [{idx}/{len(product_links)}] "
                  f"⏱️ {int(elapsed/60)}p{int(elapsed%60)}s "
                  f"(Còn ~{int(remaining/60)}p)")
        
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
        
    except Exception as e:
        errors.append({"url": url, "error": str(e)})
        print(f"  ❌ [{idx}] Lỗi: {url[:50]}... - {e}")
        continue

# ================= EXPORT TO EXCEL =================
driver.quit()

total_time = time.time() - start_time
minutes = int(total_time // 60)
seconds = int(total_time % 60)

if rows:
    df = pd.DataFrame(rows)
    df = df.map(clean_excel)

    # Convert to string
    for col in ["rating_score", "count_rate", "sold_count", "first_comment"]:
        if col in df.columns:
            df[col] = df[col].astype(str).replace('None', '').replace('nan', '')

    # Export
    df.to_excel(OUTPUT_FILE, index=False)

    print(f"\n{'='*80}")
    print(f"✅ HOÀN THÀNH!")
    print(f"{'='*80}")
    print(f"📊 Thống kê:")
    print(f"  • Tổng sản phẩm: {len(df)}")
    print(f"  • Có price: {df['price'].notna().sum()} ({df['price'].notna().sum()/len(df)*100:.1f}%)")
    print(f"  • Có size: {df['size'].notna().sum()} ({df['size'].notna().sum()/len(df)*100:.1f}%)")
    print(f"  • Có color: {df['color'].notna().sum()} ({df['color'].notna().sum()/len(df)*100:.1f}%)")
    print(f"  • Có rating: {df['rating_score'].str.len().gt(0).sum()}")
    print(f"  • Có đã bán: {df['sold_count'].str.len().gt(0).sum()}")
    print(f"  • Lỗi: {len(errors)}")
    print(f"\n⏱️  Thời gian: {minutes} phút {seconds} giây")
    print(f"📄 File xuất: {OUTPUT_FILE}")
    print(f"{'='*80}\n")
    
    # Preview
    print("📋 PREVIEW 5 SẢN PHẨM ĐẦU:")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_colwidth', 30)
    print(df[['name', 'price', 'size', 'color']].head().to_string(index=False))
    
    if errors:
        print(f"\n⚠️ Có {len(errors)} lỗi - Chi tiết:")
        for err in errors[:5]:
            print(f"  • {err['url'][:60]}... - {err['error']}")
    
else:
    print("\n❌ Không có dữ liệu để xuất!")

print(f"\n🎉 XONG! Mở file {OUTPUT_FILE} để xem kết quả.")
