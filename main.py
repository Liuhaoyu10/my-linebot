# -*- coding: utf-8 -*-
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError
from bs4 import BeautifulSoup
import requests, os

app = FastAPI()

# ======================================================
# 🔑 環境變數（在 Render 上設定）
# ======================================================
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_SECRET = os.getenv("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_TOKEN)
handler = WebhookHandler(LINE_SECRET)

# ======================================================
# 🏠 首頁測試
# ======================================================
@app.get("/")
async def root():
    return {"message": "✅ Line Bot + TCG 查價 後端運作中！"}

# ======================================================
# 💬 LINE Webhook 接收
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
# 🃏 查價功能（改用 requests + BeautifulSoup）
# ======================================================
def search_price(card_name: str):
    url = f"https://www.tcgstore.com.tw/search?sortType=Price&sortDirection=Desc&keyword={card_name}"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code != 200:
        return "⚠️ 無法連線到 TCGStore。"

    soup = BeautifulSoup(r.text, "html.parser")
    items = soup.select("a[href^='/product']")
    if not items:
        return f"❌ 找不到與「{card_name}」相關的商品。"

    results = []
    for item in items[:5]:
        title = item.select_one("h5")
        price = item.select_one("b.search-items__accent-text")
        name = title.text.strip() if title else "未知商品"
        cost = price.text.strip() if price else "無價格"
        results.append(f"{name} → {cost}")

    return "\n".join(results)

# ======================================================
# 🤖 處理訊息
# ======================================================
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    print(f"🗨️ 收到訊息: {msg}")
    reply_text = search_price(msg)
    print(f"✅ 回覆內容:\n{reply_text}")
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

# ======================================================
# 🚀 啟動伺服器
# ======================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)