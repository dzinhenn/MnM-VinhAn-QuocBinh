# Nhom-ACE32

## Giới thiệu
Dự án crawl dữ liệu sản phẩm từ website **Vua Đồ Câu** bằng Python.  
Mục tiêu của project là thu thập, xử lý và làm sạch dữ liệu sản phẩm phục vụ cho phân tích dữ liệu.

---

## Công nghệ sử dụng
- Python
- Selenium
- Pandas
- ChromeDriver
- Excel (.xlsx)

---

## Cấu trúc thư mục

Nhom-ACE32/
├── scripts/ # Mã nguồn Python
│ ├── 10product.py
│ ├── drawl_all.py
│ ├── final-craw.py
│ ├── test.py
│ └── xuli_data.py
│
├── driver/ # Công cụ hỗ trợ crawl
│ └── chromedriver.exe
│
├── data_raw/ # Dữ liệu crawl thô
│ ├── vuadocau_ALL_products.xlsx
│ ├── vuadocau_products_20251223_224640.xlsx
│ └── vuadocau_TEST_10_20251223_232448.xlsx
│
├── data_processed/ # Dữ liệu đã xử lý
│ ├── vuadocau_clean_dataset.xlsx
│ ├── vuadocau_missing_dataset.xlsx
│ ├── ketqua-final-craw.xlsx
│ └── ketqua-final-craw (1).xlsx
│
├── .gitignore
└── README.md

---

## Mô tả các script chính

- `10product.py`  
  Crawl thử nghiệm dữ liệu của 10 sản phẩm.

- `drawl_all.py`  
  Crawl toàn bộ danh sách sản phẩm, bao gồm giá, màu sắc, size.

- `final-craw.py`  
  Script hoàn chỉnh để crawl dữ liệu sản phẩm.

- `xuli_data.py`  
  Xử lý dữ liệu: làm sạch, phát hiện dữ liệu thiếu, xuất file kết quả.

- `test.py`  
  Dùng để kiểm tra logic và thử nghiệm.
## Hướng dẫn chạy project
1. Cài thư viện cần thiết
'bash'
pip install selenium pandas openpyxl
2. Kiểm tra ChromeDriver
Đảm bảo chromedriver.exe phù hợp với phiên bản Chrome đang dùng
Đường dẫn trong code:
driver = webdriver.Chrome("driver/chromedriver.exe")
3. Chạy script
python scripts/final-craw.py
Ghi chú
Các file Excel bắt đầu bằng ~$ là file tạm của Excel và đã được loại bỏ bằng .gitignore

Project phục vụ mục đích học tập và nghiên cứu
