import asyncio
from playwright.async_api import async_playwright
from lxml import html
import random
import os
import httpx
from datetime import datetime
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

cert_content = os.environ.get("CA_CERT_CONTENT")
if cert_content:
    with open("ca.pem", "w") as f:
        f.write(cert_content)
        
def setup_database():
    try:
        db = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME"),
            port=int(os.getenv("DB_PORT")),
            ssl_ca="ca.pem"
        )
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fruit_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                fruit_name VARCHAR(50),
                rarity VARCHAR(50),
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
        db.close()
        print("Database Table Verified/Created.")
    except Exception as e:
        print(f"Setup Error: {e}")

def save_to_aiven(name, rarity):
    try:
        db = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME"),
            port=int(os.getenv("DB_PORT")),
            ssl_ca="ca.pem",
            buffered=True
        )
        cursor = db.cursor()
        sql = "INSERT INTO fruit_history (fruit_name, rarity) VALUES (%s, %s)"
        cursor.execute(sql, (name, rarity))
        db.commit()
        db.close()
        print(f"Data Logged: {name}")
    except Exception as e:
        print(f"Insert Error: {e}")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "LOCAL_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "LOCAL_ID")

async def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, data={"chat_id": CHAT_ID, "text": message})
        except Exception as e:
            print(f"Telegram failed: {e}")

async def run_calibration():
    setup_database()

    if os.getenv("GITHUB_ACTIONS") == "true":
        delay = random.randint(900, 1080)
        print(f"Human Mimicry: Waiting {delay//60} mins...")
        await asyncio.sleep(delay)
        print("Starting calibration...")

    async with async_playwright() as p:
        print("Launching Stealth Submarine...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            print("Navigating to Blox Fruits Stock...")
            await page.goto("https://blox-fruits.fandom.com/wiki/Blox_Fruits_%22Stock%22", timeout=60000)
            await page.evaluate("window.scrollTo(0, 800)")
            
            await page.wait_for_selector("#mw-customcollapsible-Current", state="visible", timeout=45000)
            await asyncio.sleep(2)
            content = await page.content()
            await browser.close()
 
        except Exception as e:
            print(f"Error: {e}")
            await page.screenshot(path="debug_view.png")
            await browser.close()
            return

        tree = html.fromstring(content)
        treasure = tree.xpath('//*[@id="mw-customcollapsible-Current"]//div[@class="fruit-stock"]')

        if not treasure:
            print("Map Error: Stock containers not found.")
            return
        
        print(f"\n{'='*10} RESULTS {'='*10}")
        current_time = datetime.now().strftime("%H:%M")
        print(f"Calibration Time: {current_time}")

        for box in treasure:
            name_data = box.xpath('.//span[contains(@class, "Outline")]//a/text()')
            class_data = box.xpath('.//span[contains(@class, "Outline")]/@class')

            if name_data and class_data:
                name = name_data[0].strip()
                rarity = class_data[0].split("--")[-1].replace(")", "").replace(" Outline-B", "")

                if rarity == "Common":
                    continue 
                
                save_to_aiven(name, rarity)

                targets = ["Tiger", "Control", "Kitsune", "Dragon", "Gravity", "Lightning"]
                if rarity in ["Mythical", "Legendary"] or name in targets:
                    status = f"🚨 {rarity.upper()} DETECTED: {name} at {current_time}!"
                    print(status)
                    await send_telegram(status)
                else:
                    print(f"Found {name} ({rarity})")

        print(f"{'='*29}\n")

if __name__ == "__main__":
    asyncio.run(run_calibration())