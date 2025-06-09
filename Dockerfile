# 使用官方 Python 映像檔作為基礎
FROM python:3.10-slim

# 設定工作目錄
WORKDIR /app

# 將 requirements.txt 複製到工作目錄中
COPY requirements.txt .

# 安裝所需的套件
RUN pip install --no-cache-dir -r requirements.txt

# 安裝 Playwright 所需的瀏覽器及作業系統依賴
# 這一步很重要，否則在 Docker 容器中會無法執行
RUN playwright install --with-deps chromium

# 將專案的其餘程式碼複製到工作目錄中
COPY . .

# 設定容器啟動時要執行的命令
CMD ["python", "main.py"] 