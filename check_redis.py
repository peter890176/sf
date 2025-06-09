# check_redis.py

import redis
import json

# --- 設定 ---
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
# 要查詢的資料分類
CATEGORIES_TO_CHECK = ['text', 'image', 'video', 'reel']
# --- 設定結束 ---

def main():
    """
    連接到 Redis，讀取指定分類的資料，並以格式化的 JSON 打印出來。
    """
    print(f"正在連接到 Redis ({REDIS_HOST}:{REDIS_PORT})...")
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
        print("Redis 連接成功！\n")
    except redis.exceptions.ConnectionError as e:
        print(f"錯誤：無法連接到 Redis。請確認 Docker 容器正在運行中。")
        print(f"錯誤訊息: {e}")
        return

    total_posts_found = 0
    for category in CATEGORIES_TO_CHECK:
        key = f"category:{category}"
        # 使用 hgetall 獲取該 key 下所有的 hash 資料
        all_posts_in_category = r.hgetall(key)
        
        if not all_posts_in_category:
            continue

        print("=" * 20 + f" 分類: {category.upper()} " + "=" * 20)
        
        for post_uid, post_json in all_posts_in_category.items():
            total_posts_found += 1
            print(f"--- UID: {post_uid} ---")
            
            # 將 JSON 字串解析為 Python 字典，並以縮排格式打印
            post_data = json.loads(post_json)
            print(json.dumps(post_data, indent=4, ensure_ascii=False))
            print("-" * 40 + "\n")
            
    if total_posts_found == 0:
        print("資料庫中未找到任何貼文資料。")
    else:
        print(f"查詢完畢，共在資料庫中找到 {total_posts_found} 則貼文。")


if __name__ == "__main__":
    main() 