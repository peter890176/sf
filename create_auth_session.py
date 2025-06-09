# create_auth_session.py
import asyncio
from playwright.async_api import async_playwright

async def main():
    auth_file = "auth_state.json"
    
    async with async_playwright() as p:
        # 啟動一個非無頭的瀏覽器，這樣我們才能手動操作
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            locale="zh-TW",
            timezone_id="Asia/Taipei"
        )
        page = await context.new_page()

        print("\n" + "="*60)
        print("瀏覽器已啟動。請手動執行以下操作：")
        print("1. 在彈出的瀏覽器視窗中，前往 https://www.facebook.com")
        print("2. 輸入您的帳號和密碼。")
        print("3. 完成 CAPTCHA 真人驗證挑戰。")
        print("4. 確認您已完全登入，能看到 Facebook 主頁。")
        print("="*60 + "\n")

        await page.goto("https://www.facebook.com")

        input("...當您完成手動登入後，請回到此終端機視窗，然後按下 [Enter] 鍵以繼續...")

        # 將當前的瀏覽器狀態 (cookies, local storage 等) 儲存到檔案中
        await context.storage_state(path=auth_file)
        
        print(f"\n[成功] 認證狀態已成功儲存至 '{auth_file}'！")
        print("您現在可以關閉這個腳本，並運行主爬蟲程式了。")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main()) 