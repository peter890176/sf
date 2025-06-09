# main.py - 程式執行的進入點
import asyncio
import os
import redis
import json
from dotenv import load_dotenv
from scraper.crawler import FacebookScraper

# 在程式最開始加載 .env 檔案中的環境變數
load_dotenv()

def store_data_to_redis(redis_client, posts):
    """
    將貼文資料依照 Category 分類存入 Redis Hash。
    """
    print(f"準備將 {len(posts)} 則貼文存入 Redis...")
    for post in posts:
        if 'UID' not in post or 'Category' not in post:
            print(f"警告：貼文缺少 UID 或 Category，已跳過: {post}")
            continue
        
        # Key: category:videos, Field: post_uid, Value: post_data_json
        key = f"category:{post['Category'].lower()}"
        field = post['UID']
        value = json.dumps(post, ensure_ascii=False)
        
        try:
            redis_client.hset(key, field, value)
        except redis.RedisError as e:
            print(f"存入 Redis 時發生錯誤: {e}")
            
    print("資料已成功存入 Redis。")

async def main():
    """
    主函式，用於協調爬蟲啟動、資料處理和儲存。
    """
    print("自動化程式啟動...")
    
    # 從環境變數讀取 Redis 設定
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))

    # 1. 初始化爬蟲，傳入要搜尋的粉絲專頁名稱和專頁ID
    fan_page_name = "派拉蒙影片 官方粉絲團" # 用於搜尋框輸入
    fan_page_id = "ParamountTaiwan" # 用於在搜尋結果中精準定位連結
    scraper = FacebookScraper(
        fan_page_name=fan_page_name,
        fan_page_id=fan_page_id
    )
    
    # 2. 開始執行自動化任務
    posts = await scraper.scrape()

    if not posts:
        print("未抓取到任何資料，程式即將結束。")
        return

    try:
        # 3. 建立 Redis 連線
        r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        r.ping() # 檢查連線是否成功
        print("成功連接到 Redis。")
        
        # 4. 將資料存入 Redis
        store_data_to_redis(r, posts)
        
    except redis.exceptions.ConnectionError as e:
        print(f"無法連接到 Redis ({redis_host}:{redis_port})。請確認 Redis 服務是否正在運行。")
        print(f"錯誤訊息: {e}")

    print("自動化程式執行完畢。")

if __name__ == "__main__":
    # 使用 asyncio.run 來執行 async main 函式
    asyncio.run(main()) 