# scraper/crawler.py - 爬蟲邏輯 (v10)

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import uuid
import json
import re
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FacebookScraper:
    def __init__(self, fan_page_name, fan_page_id):
        self.fan_page_name = fan_page_name
        self.fan_page_id = fan_page_id
        self.posts_data = []
        self.processed_urls = set()

    async def _extract_data_from_article(self, article):
        # v10: The final version. Robust selectors based on direct analysis.
        post_data = {
            'UID': str(uuid.uuid4()),
            'PostURL': '', 'Content': '', 'ImageURL': '', 'VideoURL': '',
            'Category': 'text', 'ReactionCount': 0, 'ResponseCount': 0, 'ShareCount': 0,
        }

        try:
            # 1. Extract Post URL (must have)
            link_element = await article.query_selector('a[href*="/posts/"], a[href*="/videos/"], a[href*="/reels/"], a[href*="/photo/"], a[href*="?id="]')
            post_url = ''
            if link_element:
                href = await link_element.get_attribute('href')
                if href:
                    post_url = href.split('?')[0]
            
            if not post_url or post_url in self.processed_urls:
                return None
            post_data['PostURL'] = post_url

            # 2. Click "See more" to expand content
            try:
                see_more_button = await article.query_selector('div[role="button"]:has-text("查看更多")')
                if see_more_button:
                    await see_more_button.click()
                    await asyncio.sleep(0.5)
            except Exception: pass

            # 3. Extract Content
            content_element = await article.query_selector('div[data-ad-preview="message"]')
            if content_element:
                post_data['Content'] = await content_element.inner_text()
            else:
                 content_element = await article.query_selector('div[dir="auto"][style*="text-align: start;"]')
                 if content_element:
                     post_data['Content'] = await content_element.inner_text()

            # 4. Categorize and Extract Media URL
            if '/reels/' in post_url:
                post_data['Category'] = 'reel'
                video_tag = await article.query_selector('video')
                if video_tag: post_data['VideoURL'] = await video_tag.get_attribute('src')
            elif '/videos/' in post_url:
                post_data['Category'] = 'video'
                video_tag = await article.query_selector('video')
                if video_tag: post_data['VideoURL'] = await video_tag.get_attribute('src')
            else:
                image_tag = await article.query_selector('a[href*="/photo"] img[src]')
                if image_tag:
                    post_data['Category'] = 'image'
                    post_data['ImageURL'] = await image_tag.get_attribute('src')
                else:
                    post_data['Category'] = 'text'

            # 5. Extract Counts from the footer area
            # This is the most reliable method as counts are grouped here.
            footer_area = await article.query_selector('div[class="x1i10hfl x1jx94hy xjbqb8w x1ypdohk x1rg5ohu x1pc53ja x12b2p6s"]')
            if footer_area:
                footer_text = await footer_area.inner_text()

                # Reactions: in a specific aria-hidden span
                try:
                    reaction_span = await footer_area.query_selector('span[aria-hidden="true"]')
                    if reaction_span:
                        text = await reaction_span.inner_text()
                        if text.isdigit():
                            post_data['ReactionCount'] = int(text)
                except Exception: pass
                
                # Comments: use regex on the footer text
                try:
                    comment_match = re.search(r'(\d+)\s*則留言', footer_text)
                    if comment_match:
                        post_data['ResponseCount'] = int(comment_match.group(1))
                except Exception: pass

                # Shares: use regex on the footer text
                try:
                    share_match = re.search(r'(\d+)\s*次分享', footer_text)
                    if share_match:
                        post_data['ShareCount'] = int(share_match.group(1))
                except Exception: pass
            
            self.processed_urls.add(post_url)
            return post_data

        except Exception as e:
            logging.error(f"Error extracting data from article: {e}")
            return None

    async def scrape(self):
        logging.info("Automation process starting... (Visitor Mode)")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                locale="zh-TW",
                timezone_id="Asia/Taipei",
                java_script_enabled=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                target_url = f"https://www.facebook.com/{self.fan_page_id}/posts"
                logging.info(f"Step 2: Navigating to target page: {target_url}")
                await page.goto(target_url, timeout=60000, wait_until="domcontentloaded")

                try:
                    logging.info("  > Checking for login popup...")
                    close_button_selector = 'div[aria-label="關閉"]'
                    await page.wait_for_selector(close_button_selector, timeout=7000)
                    logging.info("  > Popup detected, closing it...")
                    await page.locator(close_button_selector).first.click()
                    logging.info("  > Popup closed.")
                except PlaywrightTimeoutError:
                    logging.info("  > No popup detected, continuing.")

                logging.info("Step 3: Waiting for posts to load and scrolling...")
                await page.wait_for_selector('[role="article"]', timeout=30000)
                
                last_height = await page.evaluate("document.body.scrollHeight")
                patience = 5
                while patience > 0:
                    await page.mouse.wheel(0, 1500)
                    await asyncio.sleep(2)
                    new_height = await page.evaluate("document.body.scrollHeight")
                    if new_height > last_height:
                        logging.info(f"  > Scrolled, new height: {new_height}")
                        last_height = new_height
                        patience = 5
                    else:
                        patience -= 1
                        logging.info(f"  > No new content after scroll. Patience: {patience}")
                
                logging.info("Scrolling finished.")

                logging.info("Saving current page HTML for debugging (debug_page.html)...")
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(await page.content())
                logging.info("HTML saved.")

                logging.info("Extracting all posts from the downloaded content...")
                all_articles = await page.query_selector_all('[role="article"]')
                logging.info(f"Found {len(all_articles)} [role=\"article\"] elements to process.")
                
                tasks = [self._extract_data_from_article(article) for article in all_articles]
                results = await asyncio.gather(*tasks)
                
                self.posts_data = [res for res in results if res]

            except Exception as e:
                logging.error(f"An error occurred during the automation process: {e}")
            finally:
                logging.info("Taking final screenshot `visitor_mode_end_screenshot.png`...")
                await page.screenshot(path="visitor_mode_end_screenshot.png", full_page=True)
                logging.info("Screenshot saved.")
                await context.close()
                await browser.close()

        logging.info(f"Automation finished. Downloaded {len(self.posts_data)} posts.")
        return self.posts_data

# 移除了舊的測試區塊，因為它依賴於已被棄用的 cookie 登入方式 