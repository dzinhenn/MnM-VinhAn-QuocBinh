import pandas as pd
import re

# đọc file Excel gốc
df = pd.read_excel(
    r"D:\PYTHON\project\vuadocau\xulidata\ketqua-final-craw (1).xlsx"
)
print("Số dòng ban đầu:", len(df))

# đổi tên cột
COLUMN_MAPPING = {
    "name": "product_name",
    "price": "price_raw",
    "size": "size_raw",
    "rating": "rating",
    "review_count": "review_count",
    "url": "product_url"
}
df = df.rename(columns={k: v for k, v in COLUMN_MAPPING.items() if k in df.columns})

# xoá xuống dòng cho Excel gọn
TEXT_COLUMNS = ["product_name", "price_raw", "size_raw", "product_url"]
for col in TEXT_COLUMNS:
    if col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(r"[\r\n]+", " ", regex=True)
            .str.strip()
        )

# === XỬ LÝ GIÁ: XOÁ TRÙNG + GHI ĐÈ LẠI price_raw ===
def normalize_price(price_raw):
    if pd.isna(price_raw):
        return "", []

    parts = re.split(r"\||/", str(price_raw))
    nums = []
    for p in parts:
        nums.extend(re.findall(r"\d{4,}", p))

    unique_prices = sorted(set(int(n) for n in nums))

    # ghi lại price_raw cho gọn
    price_raw_clean = " | ".join(str(p) for p in unique_prices)

    return price_raw_clean, unique_prices


df[["price_raw", "price_list"]] = df["price_raw"].apply(
    lambda x: pd.Series(normalize_price(x))
)

# === PHÂN LOẠI SẢN PHẨM ===
def classify_product(name):
    name = str(name).lower()
    if "cần câu tay" in name or "can cau tay" in name:
        return "can_cau_tay"
    if "cần câu" in name and "máy" in name:
        return "can_cau_may"
    if "máy câu ngang" in name:
        return "may_cau_ngang"
    if "máy câu đứng" in name:
        return "may_cau_dung"
    if "mồi" in name or "lure" in name:
        return "moi_cau"
    if "phao" in name:
        return "phao"
    if "dây" in name or "cước" in name:
        return "day_cuoc"
    if "lưỡi" in name:
        return "luoi_cau"
    return "khac"

df["product_type"] = df["product_name"].apply(classify_product)

# ép kiểu nhẹ
for c in ["rating", "review_count"]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

print("Số dòng sau xử lý:", len(df))


df.to_csv("vuadocau.csv", index=False, encoding="utf-8-sig")
print("Đã lưu vuadocau.csv")
