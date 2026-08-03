import requests
from bs4 import BeautifulSoup
import hashlib
import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

URL = "https://kelabgasingbeyblade.my/beyblade-x?category_id=1&page=1"

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": text
    })

def check_stock():

    r = requests.get(URL)
    soup = BeautifulSoup(r.text, "html.parser")

    products = soup.get_text(" ", strip=True)

    current = hashlib.md5(products.encode()).hexdigest()

    old = ""

    if os.path.exists("stock.txt"):
        old = open("stock.txt").read()

    if current != old:

        send_message(
            "🔔 Beyblade X 页面有变化！\n\n"
            "可能有补货或新品更新：\n"
            + URL
        )

        open("stock.txt","w").write(current)

check_stock()
