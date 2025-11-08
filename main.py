# -*- coding: utf-8 -*-
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import os, time

# ======================================================
# 🔑 從 Render 環境變數讀取金鑰（記得在 Render 介面設定）
# ======================================================
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# ======================================================
# 🧠 初始化 FastAPI + LINE Bot
# ======================================================
app = FastAPI()
line_bot_api = LineBotApi(LINE_TOKEN)
handler = WebhookHandler(LINE_SECRET)

# ======================================================
# 🏠 首頁測試
# ======================================================
@app.get("/")
async def root():
    return {"message": "✅ Line Bot + TCG 查價後端運作中！"}

# ======================================================
# 💬 Webhook 接收事件
# ======================================================
@app.post("/callback")
async def callback(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")
    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        return PlainTextResponse("Invalid signature", status_code=400)
    return PlainTextResponse("OK")

# ======================================================
# 🃏 查價功能（Selenium）
# ======================================================
def search_price(card_name: str):
    base_url = "https://www.tcgstore.com.tw/search"
    url = f"{base_url}?sortType=Price&sortDirection=Desc&keyword={card_name}"

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Render 上安裝的 chromedriver 通常在 /usr/bin/chromedriver
    driver = webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=options)
    driver.get(url)
    time.sleep(5)

    items = driver.find_elements(By.CSS_SELECTOR, "a[href^='/product']")
    if not items:
        driver.quit()
        return f"❌ 找不到與「{card_name}」相關的商品。"

    results = []
    for item in items[:5]:  # 只取前 5 筆結果
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

# ======================================================
# 🤖 處理使用者訊息事件
# ======================================================
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    print(f"🗨️ 收到使用者訊息: {msg}")

    # Selenium 查價
    reply_text = search_price(msg)
    print(f"✅ 回覆內容：\n{reply_text}")

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

# ======================================================
# 🚀 啟動伺服器
# ======================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))  # ✅ 必須使用 Render 的動態 PORT
    uvicorn.run("main:app", host="0.0.0.0", port=port)
