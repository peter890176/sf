# check_redis.py

import redis
import json
import os
from bs4 import BeautifulSoup

# --- 設定 ---
REDIS_HOST = 'redis'
REDIS_PORT = 6379
# 要查詢的資料分類
CATEGORIES = ['text', 'image', 'video', 'reel']
# Redis key 的前綴
KEY_PREFIX = 'fb_post:'

def check_redis_data():
    """連接到 Redis 並讀取所有 'fb_post:*' 的資料。"""
    try:
        # 使用服務名稱 'redis' 而不是 'localhost'
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        r.ping() 
        print("Redis 連接成功！")
    except redis.exceptions.ConnectionError as e:
        print(f"無法連接到 Redis。請確保 Redis 容器正在運行。")
        print(f"錯誤訊息: {e}")
        return

    keys = r.keys(f'{KEY_PREFIX}*')
    
    if not keys:
        print("在 Redis 中找不到任何貼文資料。")
        return

    print(f"\n==================== Redis 資料庫中的貼文 ====================\n")
    
    posts_by_category = {cat: [] for cat in CATEGORIES}

    for key in keys:
        try:
            post_data_json = r.get(key)
            if post_data_json:
                post_data = json.loads(post_data_json)
                category = post_data.get('Category', 'text')
                if category in posts_by_category:
                    posts_by_category[category].append(post_data)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"無法解析 Redis key '{key}' 的資料: {e}")
            raw_data = r.get(key)
            print(f"原始資料: {raw_data}")


    total_posts = 0
    for category, posts in posts_by_category.items():
        if posts:
            print(f"==================== 分類: {category.upper()} ====================")
            for post in posts:
                print(f"--- UID: {post.get('UID', 'N/A')} ---")
                print(json.dumps(post, indent=4, ensure_ascii=False))
                print("----------------------------------------\n")
            total_posts += len(posts)

    print(f"查詢完畢，共在資料庫中找到 {total_posts} 則貼文。")


def analyze_debug_html():
    """讀取並解析 debug_page.html，輸出第一個 article 的結構。"""
    print("\n==================== HTML 偵錯分析 ====================")
    html_path = 'debug_page.html'
    if not os.path.exists(html_path):
        print(f"錯誤: 找不到 '{html_path}'。請先執行爬蟲以產生此檔案。")
        return

    print(f"正在讀取 '{html_path}'...")
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    print("使用 BeautifulSoup 進行解析...")
    soup = BeautifulSoup(html_content, 'lxml')
    
    first_article = soup.find('div', attrs={'role': 'article'})
    
    if first_article:
        print("\n--- 找到第一個 [role='article'] 元素的完整 HTML 結構 ---\n")
        # 使用 prettify() 來美化輸出
        print(first_article.prettify())
        print("\n--- HTML 結構輸出完畢 ---\n")
    else:
        print("\n錯誤: 在 HTML 中找不到任何 [role='article'] 的元素。\n")


if __name__ == '__main__':
    # 首先，我們先來分析最重要的 HTML 檔案
    analyze_debug_html()
    
    # 然後，我們再檢查一次 Redis 裡的資料
    check_redis_data() 