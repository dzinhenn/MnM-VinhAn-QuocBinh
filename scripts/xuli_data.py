import pandas as pd
import re

# ================= LOAD =================
INPUT_FILE = r"D:\PYTHON\project\vuadocau\xulidata\ketqua-final-craw (1).xlsx"
OUTPUT_CLEAN = r"D:\PYTHON\project\vuadocau\xulidata\vuadocau_clean_dataset.xlsx"
OUTPUT_MISSING = r"D:\PYTHON\project\vuadocau\xulidata\vuadocau_missing_dataset.xlsx"

df = pd.read_excel(INPUT_FILE)

print("📄 Kích thước ban đầu:", df.shape)
print(df.head())



# ================= STANDARDIZE COLUMNS =================
df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)

# ================= STRIP TEXT =================
for col in df.select_dtypes(include="object").columns:
    df[col] = df[col].astype(str).str.strip()

# ================= HANDLE MISSING =================
df["size"] = df["size"].replace({"": None, "nan": None})
df["price"] = df["price"].replace({"": None, "nan": None})

# ================= CLEAN PRICE =================
def clean_price(x):
    if pd.isna(x):
        return None
    x = re.sub(r"[^\d]", "", str(x))
    return int(x) if x else None

df["price_clean"] = df["price"].apply(clean_price)

# ================= CLEAN SIZE =================
def clean_size(x):
    if pd.isna(x):
        return None
    # 4m5 -> 4.5 | 10m -> 10
    m = re.search(r"(\d+)m(\d+)?", str(x))
    if not m:
        return None
    if m.group(2):
        return float(f"{m.group(1)}.{m.group(2)}")
    return float(m.group(1))

df["size_m"] = df["size"].apply(clean_size)

# ================= REMOVE DUPLICATES =================
df = df.drop_duplicates(
    subset=["name", "size_m", "price_clean", "product_url"]
)

# ================= SPLIT DATA =================
df_clean = df[
    df["size_m"].notna() & df["price_clean"].notna()
]

df_missing = df[
    df["size_m"].isna() | df["price_clean"].isna()
]

# ================= EXPORT =================
df_clean.to_excel(OUTPUT_CLEAN, index=False)
df_missing.to_excel(OUTPUT_MISSING, index=False)

# ================= REPORT =================
print("\n✅ XỬ LÝ HOÀN TẤT")
print("📄 Dataset sạch:", df_clean.shape)
print("⚠️ Dataset thiếu dữ liệu:", df_missing.shape)
print("📁 File sạch:", OUTPUT_CLEAN)
print("📁 File thiếu:", OUTPUT_MISSING)
