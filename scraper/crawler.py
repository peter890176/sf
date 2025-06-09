# scraper/crawler.py - 爬蟲邏輯

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import uuid
import json
import re
import os # 引入 os 模組來檢查檔案是否存在

class FacebookScraper:
    def __init__(self, fan_page_name, fan_page_id):
        self.fan_page_name = fan_page_name
        self.fan_page_id = fan_page_id
        self.posts_data = []
        self.processed_urls = set()
        self.auth_file = "auth_state.json"

    def _parse_count(self, text: str) -> int:
        """將 '1.2萬' 或 '3.4K' 這類字串轉換為整數"""
        text = text.lower().strip()
        if not text:
            return 0
        
        number_part = re.search(r'[\d\.]+', text)
        if not number_part:
            return 0
            
        num = float(number_part.group())
        
        if '萬' in text:
            num *= 10000
        elif 'k' in text:
            num *= 1000
            
        return int(num)

    async def _extract_data_from_article(self, article):
        """從互動後的貼文元素中提取結構化資料。"""
        try:
            # 獲取貼文的永久連結
            link_element = await article.query_selector('a[href*="/posts/"], a[href*="/videos/"], a[href*="/reel/"], a[href*="/photos/"], a[href*="fbid="]')
            if not link_element: return None
            href = await link_element.get_attribute('href')
            if not href: return None
            post_url = f"https://www.facebook.com{href.split('?')[0]}" if href.startswith('/') else href.split('?')[0]

            if post_url in self.processed_urls:
                return None # 如果已經處理過，返回None

            post_data = {
                'UID': str(uuid.uuid4()),
                'PostURL': post_url,
                'Content': '',
                'ImageURL': '',
                'VideoURL': '',
                'Category': 'text',
                'ReactionCount': 0,
                'ResponseCount': 0,
            }
            content_div = await article.query_selector('div[data-ad-preview="message"]')
            if content_div: post_data['Content'] = await content_div.inner_text()
            video_element = await article.query_selector('video')
            if video_element:
                post_data['Category'] = 'video'
                post_data['VideoURL'] = await video_element.get_attribute('src')
            else:
                img_element = await article.query_selector('div[data-visualcompletion="media-vc-image"] img')
                if img_element:
                    post_data['Category'] = 'image'
                    post_data['ImageURL'] = await img_element.get_attribute('src')
            
            # 如果 URL 包含 /reel/，則將分類覆蓋為 'reel'
            if '/reel/' in post_url:
                post_data['Category'] = 'reel'

            # 提取心情和回應數量
            # 定位到包含統計數據的容器
            stats_container = await article.query_selector('div.x9f619.x1n2onr6.x1ja2u2z.x78zum5.x2lah0s.x1qughib.x1qjc9v5')
            if stats_container:
                # 尋找所有可能的數據文字
                spans = await stats_container.query_selector_all('span.xt0b8zv.x1jx91rq.x1cp0bde.x1pu36lj.xdt5ytf')
                texts = [await span.inner_text() for span in spans]
                
                for text in texts:
                    if "則留言" in text:
                        post_data['ResponseCount'] = self._parse_count(text)
                    # 心情數通常是純數字或帶有 K/萬 的字串，且沒有其他描述
                    elif re.match(r'^[\d\.,Kk萬]+$', text.strip()):
                         post_data['ReactionCount'] = self._parse_count(text)

            self.processed_urls.add(post_url) # 標記為已處理
            return post_data
        except Exception:
            return None

    async def scrape(self):
        # 訪客模式不需要檢查認證檔案
        print("自動化流程開始... (訪客模式)")
        async with async_playwright() as p:
            # 在無頭模式下運行，但會擷取最終畫面
            browser = await p.chromium.launch(headless=True) 
            context = await browser.new_context(
                # 訪客模式不載入任何狀態
                locale="zh-TW",
                timezone_id="Asia/Taipei",
                java_script_enabled=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                # 步驟 1: 前往 Facebook
                # 我們直接前往目標頁面，這一步可以省略
                # print("步驟 1: 前往 Facebook 首頁...")
                # await page.goto("https://www.facebook.com/", timeout=60000)

                # 步驟 2: 直接構建目標 URL 並導航
                target_url = f"https://www.facebook.com/{self.fan_page_id}/posts"
                print(f"步驟 2: 直接導航至目標頁面: {target_url}")
                await page.goto(target_url, timeout=60000)

                # 步驟 2.5: 處理可能的登入/註冊彈出視窗
                try:
                    print("  > 檢查是否有登入彈出視窗...")
                    # Facebook 的關閉按鈕通常是這個選擇器
                    close_button_selector = 'div[aria-label="關閉"]'
                    close_button = page.locator(close_button_selector).first
                    # 使用一個較短的超時，因為彈窗如果出現，會很快出現
                    await close_button.wait_for(state="visible", timeout=5000)
                    print("  > 偵測到彈出視窗，正在點擊關閉按鈕...")
                    await close_button.click()
                    print("  > 彈出視窗已關閉。")
                except PlaywrightTimeoutError:
                    print("  > 未偵測到彈出視窗，正常繼續。")

                # 步驟 3: 等待貼文載入
                print("步驟 3: 成功進入貼文列表，開始下載貼文...")
                await page.wait_for_selector('[role="article"]', timeout=30000)
                
                last_height = await page.evaluate("document.body.scrollHeight")
                patience = 5

                while patience > 0:
                    visible_articles = await page.query_selector_all('[role="article"]')
                    new_posts_found_this_round = 0

                    for article in visible_articles:
                        post_data = await self._extract_data_from_article(article)
                        if post_data:
                            self.posts_data.append(post_data)
                            new_posts_found_this_round += 1
                            print(f"  > 已下載貼文: {post_data['PostURL']}")

                    print(f"本輪循環找到 {new_posts_found_this_round} 則新貼文。總數: {len(self.posts_data)}。耐心值: {patience}")

                    # 滾動
                    print("  > 執行滑鼠滾輪滾動...")
                    for _ in range(10):
                        await page.mouse.wheel(0, 500)
                        await asyncio.sleep(0.2)
                    await asyncio.sleep(2)

                    # 檢查新內容
                    new_height = await page.evaluate("document.body.scrollHeight")
                    if new_height > last_height:
                        last_height = new_height
                        patience = 5 # 重設耐心
                    else:
                        patience -= 1
                        print("  > 滾動後未發現新內容。")

                print("下載循環結束。")

            except Exception as e:
                print(f"自動化過程中發生錯誤: {e}")
            finally:
                # 在關閉瀏覽器前，擷取最終畫面以供偵錯
                print("正在擷取最終畫面 `visitor_mode_end_screenshot.png`...")
                await page.screenshot(path="visitor_mode_end_screenshot.png", full_page=True)
                print("擷取完成。")
                await context.close()
                await browser.close()

        print(f"自動化流程結束，共下載 {len(self.posts_data)} 則貼文。")
        return self.posts_data

# 移除了舊的測試區塊，因為它依賴於已被棄用的 cookie 登入方式 