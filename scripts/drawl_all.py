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
        # Tìm trong page source
        page_text = driver.page_source
        patterns = [
            r'(\d+)\s*đã\s*bán',
            r'sold[:\s]*(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                return matches[0]
        
        # Fallback: tìm element
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
    """
    FIX: Lấy size (chiều dài) và price từ variations
    """
    size_price = {}
    
    try:
        # Lấy data variations từ form
        form = driver.find_element(By.CSS_SELECTOR, "form.variations_form")
        data = form.get_attribute("data-product_variations")
        
        if not data:
            # Nếu không có variations, thử lấy giá đơn giản
            try:
                price_el = driver.find_element(By.CSS_SELECTOR, "p.price .woocommerce-Price-amount bdi")
                price_text = price_el.text.strip()
                # Parse giá: "1,150,000₫" -> "1150000"
                price_clean = re.sub(r'[^\d]', '', price_text)
                if price_clean:
                    return None, price_clean
            except:
                pass
            return None, None
        
        variations = json.loads(data)
        
        for v in variations:
            # Kiểm tra sản phẩm có bán được không
            if not v.get("is_purchasable", True):
                continue
            
            attrs = v.get("attributes", {})
            price_raw = v.get("display_price") or v.get("price")
            
            if price_raw is None:
                continue
            
            # Tìm attribute size (có thể là "size", "chieu-dai", "kich-thuoc", v.v.)
            size = None
            for key, val in attrs.items():
                key_lower = key.lower()
                # Check nhiều pattern khác nhau
                if any(keyword in key_lower for keyword in [
                    "size", "kich", "chieu", "dai", "length"
                ]):
                    size = str(val).strip()
                    break
            
            if not size:
                # Nếu không tìm được key, lấy value đầu tiên
                if attrs:
                    size = str(list(attrs.values())[0]).strip()
            
            if size and size not in size_price:
                # Format giá: loại bỏ số thập phân nếu .0
                price_val = float(price_raw)
                if price_val == int(price_val):
                    size_price[size] = str(int(price_val))
                else:
                    size_price[size] = str(price_val)
        
    except Exception as e:
        print(f"  ⚠️ Lỗi get_size_price: {e}")
        pass
    
    if not size_price:
        return None, None
    
    # Sort theo size nếu có thể (ví dụ: 4m5, 5m4, 6m3)
    try:
        # Extract số từ size string
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
    """
    FIX: Lấy màu sắc/nhóm sản phẩm
    """
    colors = []
    
    # CÁCH 1: Lấy từ color swatches/variations
    try:
        # Thử nhiều selector
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
    
    # CÁCH 2: Lấy từ variations data trong form
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
                        # Tìm attribute liên quan đến màu
                        if any(x in key_lower for x in [
                            "color", "mau", "colour", "nhom", "group"
                        ]):
                            if val and str(val).strip():
                                colors.append(str(val).strip())
        except:
            pass
    
    # CÁCH 3: Tìm trong description text (ví dụ: "Màu sắc: đỏ – đen")
    if not colors:
        try:
            # Tìm trong short description
            desc = driver.find_element(
                By.CSS_SELECTOR, 
                "div.woocommerce-product-details__short-description"
            ).text
            
            # Pattern: "Màu sắc: xxx"
            color_match = re.search(
                r'[Mm]àu\s*sắc\s*[:\-]\s*([^\n.]+)',
                desc
            )
            if color_match:
                color_str = color_match.group(1).strip()
                # Split by common separators
                color_parts = re.split(r'[,;–\-/]', color_str)
                colors = [c.strip() for c in color_parts if c.strip()]
        except:
            pass
    
    # CÁCH 4: Tìm GP-XXX pattern
    if not colors:
        try:
            gps = re.findall(r'GP-\d+', driver.page_source, flags=re.IGNORECASE)
            gps = sorted(set(g.upper() for g in gps))
            
            if gps:
                nums = [int(g.split("-")[1]) for g in gps]
                # Nếu là dãy liên tiếp
                if len(nums) > 2 and max(nums) - min(nums) == len(nums) - 1:
                    return f"GP-{min(nums)} ~ GP-{max(nums)}"
                return " | ".join(gps)
        except:
            pass
    
    # CÁCH 5: Tìm trong product title
    if not colors:
        try:
            title = driver.find_element(By.TAG_NAME, "h1").text
            gp_match = re.search(r'[\(\[\-\s]+(GP-\d+)', title, re.IGNORECASE)
            if gp_match:
                return gp_match.group(1).upper()
        except:
            pass
    
    if colors:
        # Loại bỏ duplicate, giữ thứ tự
        unique_colors = list(dict.fromkeys(colors))
        return " | ".join(unique_colors)
    
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
        next_btn = driver.find_element(By.CSS_SELECTOR, "a.next.page-numbers")
        next_btn.click()
        time.sleep(2)
    except:
        print("✅ Đã hết trang")
        break

product_links = list(product_links)
print(f"🔗 Tổng sản phẩm: {len(product_links)}")

# ================= SCRAPE ALL =================
rows = []

for idx, url in enumerate(product_links, start=1):
    print(f"📦 [{idx}/{len(product_links)}] {url}")
    
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
        print(f"  ❌ Lỗi khi cào {url}: {e}")
        continue

# ================= EXPORT =================
driver.quit()

if rows:
    df = pd.DataFrame(rows)

    # Làm sạch ký tự cấm Excel
    df = df.map(clean_excel)

    # Convert to string để không hiện 0
    for col in ["rating_score", "count_rate", "sold_count", "first_comment"]:
        if col in df.columns:
            df[col] = df[col].astype(str).replace('None', '').replace('nan', '')

    df.to_excel(OUTPUT_FILE, index=False)

    print(f"\n✅ HOÀN THÀNH – Đã cào {len(df)} sản phẩm")
    print(f"📄 File: {OUTPUT_FILE}")
else:
    print("\n⚠️ Không có dữ liệu để lưu!")
