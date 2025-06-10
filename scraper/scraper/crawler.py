# scraper/crawler.py - 爬蟲邏輯 (v10)

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import uuid
import json
import re
import logging
from urllib.parse import urljoin

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FacebookScraper:
    def __init__(self, fan_page_name, fan_page_id):
        self.fan_page_name = fan_page_name
        self.fan_page_id = fan_page_id
        self.base_url = "https://www.facebook.com"
        self.posts_data = []
        self.processed_urls = set()

    async def _extract_data_from_article(self, article_element):
        """
        v24: Add "See More" click and robust category detection.
        """
        post_data = {
            'UID': str(uuid.uuid4()),
            'ReactionCount': 0, 'ResponseCount': 0, 'ShareCount': 0,
            'Category': 'text' # Default category
        }
        
        try:
            # 1. Extract Post URL and Timestamp
            perm_link_selector = 'a[href*="/posts/"], a[href*="story_fbid="]'
            link_element = await article_element.query_selector(perm_link_selector)

            if not link_element:
                logging.warning("v23: Could not find a permalink. Skipping article.")
                return None

            post_url = await link_element.get_attribute('href')
            post_url = urljoin(self.base_url, post_url).split('?')[0]

            if post_url in self.processed_urls:
                logging.info(f"v23: Skipping already processed URL: {post_url}")
                return None
            
            self.processed_urls.add(post_url)
            post_data['PostURL'] = post_url
            post_data['Timestamp'] = await link_element.inner_text()
            logging.info(f"v24: Processing Post URL: {post_url}")

            # 2. Click "See More" to expand content
            try:
                # This selector is more reliable for the "See more" button
                see_more_selector = 'div[role="button"]:has-text("查看更多")'
                see_more_button = await article_element.query_selector(see_more_selector)
                if see_more_button:
                    await see_more_button.click()
                    await asyncio.sleep(1) # Wait for content to load
                    logging.info("v24: Clicked 'See More' to expand content.")
            except Exception as e:
                logging.warning(f"v24: 'See More' button not found or not clickable: {e}")

            # 3. Extract Content (after expansion)
            content_selector = 'div[data-ad-preview="message"], div[data-ad-preview="caption"]'
            content_element = await article_element.query_selector(content_selector)
            post_data['Content'] = await content_element.inner_text() if content_element else ""

            # 4. Detect Category by content
            video_element = await article_element.query_selector('video')
            if video_element:
                post_data['Category'] = 'video'
            else:
                image_element = await article_element.query_selector('img[data-visualcompletion="media-vc-image"]')
                if image_element:
                    post_data['Category'] = 'image'
                else:
                    post_data['Category'] = 'text'

            # 5. Extract all counts using number ranking
            all_spans = await article_element.query_selector_all('span')
            
            # Step 5.1: Find all numbers in spans and rank them
            all_numbers_in_spans = []
            for span in all_spans:
                text = await span.inner_text()
                if text.strip().isdigit():
                    all_numbers_in_spans.append(self._parse_count(text))

            unique_numbers = sorted(list(set(all_numbers_in_spans)), reverse=True)

            if len(unique_numbers) > 0:
                post_data['ReactionCount'] = unique_numbers[0]
            if len(unique_numbers) > 1:
                post_data['ShareCount'] = unique_numbers[1]

            # Step 5.2: Find comments separately, as they might be text ("留言")
            comment_found = False
            for span in all_spans:
                text = await span.inner_text()
                if not text: continue
                
                comment_match = re.search(r'([\d,]+)\s*則留言', text)
                if comment_match:
                    post_data['ResponseCount'] = self._parse_count(comment_match.group(1))
                    comment_found = True
                    break 
                
            if not comment_found:
                 for span in all_spans:
                    text = await span.inner_text()
                    if text and text.strip() == '留言':
                        post_data['ResponseCount'] = 0
                        break

            logging.info(f"v24: Extracted data - Category: {post_data['Category']}, Reactions: {post_data['ReactionCount']}, Comments: {post_data['ResponseCount']}, Shares: {post_data['ShareCount']}")
            return post_data

        except Exception as e:
            logging.error(f"v24: Error extracting data from an article: {e}", exc_info=True)
            return None

    def _parse_count(self, count_str):
        """
        Helper to convert formatted count string like '1,234' to an integer.
        """
        return int(count_str.replace(',', ''))

    async def scrape(self):
        logging.info("v17: Scraper process starting...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(locale="zh-TW", timezone_id="Asia/Taipei")
            self.page = await context.new_page()
            
            try:
                target_url = f"{self.base_url}/{self.fan_page_id}/posts/"
                logging.info(f"v17: Navigating to {target_url}")
                await self.page.goto(target_url, timeout=60000, wait_until="domcontentloaded")

                # Handle login popup
                try:
                    close_button = self.page.locator('div[aria-label="關閉"]').first
                    await close_button.click(timeout=7000)
                    logging.info("v17: Login popup closed.")
                except PlaywrightTimeoutError:
                    logging.info("v17: No login popup detected.")

                # Scroll to load posts
                logging.info("v17: Scrolling to load posts...")
                for _ in range(5): # Scroll 5 times to load a decent number of posts
                    await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)
                logging.info("v17: Scrolling finished.")

                # Get all article elements
                article_selector = '[role="article"]'
                logging.info(f"v17: Finding all articles with selector: {article_selector}")
                article_elements = await self.page.query_selector_all(article_selector)
                logging.info(f"v17: Found {len(article_elements)} articles.")

                # Process each article
                for article_element in article_elements:
                    post_data = await self._extract_data_from_article(article_element)
                    if post_data:
                        self.posts_data.append(post_data)
                
            except Exception as e:
                logging.error(f"v1t: An error occurred during the main scrape process: {e}", exc_info=True)
            finally:
                await browser.close()

        logging.info(f"v17: Scraper finished. Processed {len(self.posts_data)} posts.")
        return self.posts_data

# 移除了舊的測試區塊，因為它依賴於已被棄用的 cookie 登入方式 