# main.py
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import os, time

app = FastAPI()

# 讀取環境變數
LINE_TOKEN = os.getenv("RJP/s0ug++vF1y4jo7NuS19YptR4KGbNL9T/faxG7UcBS1nCV5r/bHEFk+/CkPQqErg/LDt/GAM8uXpSXCYbIgf2WToIyuVB3pS7cZ1gt5CuhfgllrVMFY1yqiTAPxsCiQCRzKkWWjAlq07A466SZQdB04t89/1O/w1cDnyilFU=")
LINE_SECRET = os.getenv("8fc2ab41aaffc5096178aac0a241108d")

line_bot_api = LineBotApi(LINE_TOKEN)
handler = WebhookHandler(LINE_SECRET)

@app.get("/")
async def root():
    return {"message": "✅ Line Bot + TCG 查價後端運作中！"}

@app.post("/callback")
async def callback(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")
    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        return PlainTextResponse("Invalid signature", status_code=400)
    return PlainTextResponse("OK")

# 🃏 查價功能（Render 雲端 Chrome）
def search_price(card_name):
    base_url = "https://www.tcgstore.com.tw/search"
    url = f"{base_url}?sortType=Price&sortDirection=Desc&keyword={card_name}"

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=options)
    driver.get(url)
    time.sleep(5)

    items = driver.find_elements(By.CSS_SELECTOR, "a[href^='/product']")
    if not items:
        driver.quit()
        return f"❌ 找不到與「{card_name}」相關的商品。"

    results = []
    for item in items[:5]:
        try:
            title = item.find_element(By.CSS_SELECTOR, "h5").text.strip()
        except:
            title = "未知商品"
        try:
            price = item.find_element(By.CSS_SELECTOR, "b.search-items__accent-text").text.strip()
        except:
            price = "無價格"
        results.append(f"{title} → {price}")
    driver.quit()
    return "\n".join(results)

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()

    if msg.startswith("查價"):
        keyword = msg.replace("查價", "").strip()
        if not keyword:
            reply_text = "請輸入卡片名稱，例如：查價 皮卡丘"
        else:
            reply_text = search_price(keyword)
    else:
        reply_text = "請輸入「查價 卡名」查詢卡片價格，例如：查價 黑魔導"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
