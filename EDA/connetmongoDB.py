import pandas as pd
from pymongo import MongoClient

df = pd.read_csv(r"D:\PYTHON\project\vuadocau\truyvan\vuadocau.csv", encoding="utf-8-sig")

client = MongoClient("mongodb://localhost:27017")
db = client["vuadocau"]
col = db["products"]

# xoá collection cũ (nếu muốn import lại)
col.delete_many({})

# insert dữ liệu
records = df.to_dict("records")
col.insert_many(records)

print("Đã import", len(records), "document vào MongoDB")
