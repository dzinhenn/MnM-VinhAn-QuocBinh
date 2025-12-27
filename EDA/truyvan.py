import pandas as pd
import re
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["vuadocau"]
col = db["products"]
df = pd.DataFrame(list(col.find()))

df.columns = df.columns.str.lower().str.strip()

df = df.rename(columns={
    "rating_score": "rating",
    "count_rate": "review_count",
    "sold_count": "sold"
})

for c in ["rating", "review_count", "sold"]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

def get_price_by_size(size_raw, price_raw, target="4m5"):
    if pd.isna(size_raw) or pd.isna(price_raw):
        return None
    sizes = [s.strip() for s in str(size_raw).split("|")]
    prices = [
        int(re.sub(r"[^\d]", "", p))
        for p in str(price_raw).split("|")
        if re.search(r"\d", p)
    ]
    if target in sizes:
        idx = sizes.index(target)
        if idx < len(prices):
            return prices[idx]
    return None

df["price_4m5"] = df.apply(
    lambda x: get_price_by_size(x.get("size_raw"), x.get("price_raw")),
    axis=1
)

df_valid = df[
    (df["product_type"] == "can_cau_tay") &
    (df["price_4m5"].notna())
]

df_valid["revenue"] = df_valid["price_4m5"] * df_valid["sold"]

ADV_1_underpriced_hot = df_valid[
    (df_valid["price_4m5"] < df_valid["price_4m5"].quantile(0.25)) &
    (df_valid["sold"] > df_valid["sold"].quantile(0.75))
]

ADV_2_top_revenue = df_valid.sort_values("revenue", ascending=False).head(10)

ADV_3_high_rating_low_review = df_valid[
    (df_valid["rating"] >= 4.5) &
    (df_valid["review_count"] < 5)
]

ADV_4_low_rating_high_sold = df_valid[
    (df_valid["rating"] < 4) &
    (df_valid["sold"] > df_valid["sold"].quantile(0.75))
]

ADV_5_no_comment_but_hot = df_valid[
    df_valid["first_comment"].isna() &
    (df_valid["sold"] > df_valid["sold"].quantile(0.9))
]

df_sorted = df_valid.sort_values("revenue", ascending=False)
df_sorted["cum_revenue_pct"] = (
    df_sorted["revenue"].cumsum() / df_sorted["revenue"].sum()
)
ADV_6_core_80_percent = df_sorted[df_sorted["cum_revenue_pct"] <= 0.8]

ADV_7_price_outliers = df_valid[
    (df_valid["price_4m5"] < df_valid["price_4m5"].quantile(0.01)) |
    (df_valid["price_4m5"] > df_valid["price_4m5"].quantile(0.99))
]

ADV_8_premium_but_slow = df_valid[
    (df_valid["price_4m5"] > df_valid["price_4m5"].quantile(0.8)) &
    (df_valid["sold"] < df_valid["sold"].quantile(0.3))
]

ADV_9_good_value_scalable = df_valid[
    (df_valid["rating"] >= 4.5) &
    (df_valid["price_4m5"] <= df_valid["price_4m5"].median()) &
    (df_valid["sold"] > df_valid["sold"].median())
]

ADV_10_fragile_rating = df_valid[
    (df_valid["rating"] >= 4.8) &
    (df_valid["review_count"] <= 3)
]

def show(title, data, n=5):
    print(f"\n{title}")
    if data.empty:
        print("Không có dữ liệu")
    else:
        print(
            data[
                ["product_name", "price_4m5", "rating", "review_count", "sold", "revenue"]
            ].head(n)
        )
        print("Số dòng:", len(data))

show("ADV1 – Giá thấp nhưng bán cực chạy", ADV_1_underpriced_hot)
show("ADV2 – Top sản phẩm gánh doanh thu", ADV_2_top_revenue)
show("ADV3 – Rating cao nhưng review ít (rủi ro niềm tin)", ADV_3_high_rating_low_review)
show("ADV4 – Rating thấp nhưng bán mạnh (do giá / thương hiệu)", ADV_4_low_rating_high_sold)
show("ADV5 – Không comment nhưng bán rất tốt", ADV_5_no_comment_but_hot)
show("ADV6 – Nhóm sản phẩm gánh 80% doanh thu", ADV_6_core_80_percent)
show("ADV7 – Giá bất thường (cần kiểm tra)", ADV_7_price_outliers)
show("ADV8 – Cao cấp nhưng bán chậm", ADV_8_premium_but_slow)
show("ADV9 – Giá trị tốt, có thể scale", ADV_9_good_value_scalable)
show("ADV10 – Rating cao nhưng thiếu dữ liệu đánh giá", ADV_10_fragile_rating)
