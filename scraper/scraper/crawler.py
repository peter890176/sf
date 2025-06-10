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
        v23: Final simplified & robust extraction method based on number ranking.
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
            logging.info(f"v22: Processing Post URL: {post_url}")

            if '/videos/' in post_url or '/reel/' in post_url:
                post_data['Category'] = 'video'
            elif '/photos/' in post_url or '/photo/' in post_url:
                post_data['Category'] = 'image'

            # 2. Extract Content
            content_selector = 'div[data-ad-preview="message"], div[data-ad-preview="caption"]'
            content_element = await article_element.query_selector(content_selector)
            post_data['Content'] = await content_element.inner_text() if content_element else ""

            # 3. Extract all counts using number ranking
            all_spans = await article_element.query_selector_all('span')
            
            # Step 3.1: Find all numbers in spans and rank them
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

            # Step 3.2: Find comments separately, as they might be text ("留言")
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

            logging.info(f"v23: Extracted counts - Reactions: {post_data['ReactionCount']}, Comments: {post_data['ResponseCount']}, Shares: {post_data['ShareCount']}")
            return post_data

        except Exception as e:
            logging.error(f"v23: Error extracting data from an article: {e}", exc_info=True)
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