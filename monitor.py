import os
import requests
from bs4 import BeautifulSoup

# 从环境变量读取 Telegram 参数
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")

# 17 个重点关注商品及其对应网址
VIP_ITEMS = {
    "BX-34": "https://kelabgasingbeyblade.my/products/bx-34-cobalt-dragoon-2-60c",
    "BX-45": "https://kelabgasingbeyblade.my/products/bx-45-booster-samurai-calibur-6-70m",
    "BX-49": "https://kelabgasingbeyblade.my/products/bx-49-dran-strike-4-50ff",
    "BX-50": "https://kelabgasingbeyblade.my/products/bx-50-random-booster-vol11",
    "BXG-09": "https://kelabgasingbeyblade.my/products/bxg-09-cobalt-dragoon-2-60c",
    "CX-01": "https://kelabgasingbeyblade.my/products/cx-01-dran-brave-s6-60v",
    "CX-11": "https://kelabgasingbeyblade.my/products/cx-11-emperor-might-deck-set",
    "CX-12": "https://kelabgasingbeyblade.my/products/cx-12-phoenix-flare-z9-80ww",
    "CX-14": "https://kelabgasingbeyblade.my/products/cx-14-knightfortress-gv8-70un",
    "CX-18": "https://kelabgasingbeyblade.my/products/cx-18-brachio-whip-select",
    "UX-01": "https://kelabgasingbeyblade.my/products/ux-01-dran-buster-1-60a",
    "UX-03": "https://kelabgasingbeyblade.my/products/ux-03-wizard-rod-5-70b",
    "UX-06": "https://kelabgasingbeyblade.my/products/ux-06-leon-crest-7-60gn",
    "UX-11": "https://kelabgasingbeyblade.my/products/ux-11-impact-drake-9-60lr",
    "UX-13": "https://kelabgasingbeyblade.my/products/ux-13-golem-rock-1-60un",
    "UX-15": "https://kelabgasingbeyblade.my/products/ux-15-shark-scale-deck-set",
    "UX-17": "https://kelabgasingbeyblade.my/products/ux-17-meteor-dragoon-3-70j"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def send_telegram_msg(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ 未设置 BOT_TOKEN 或 CHAT_ID！")
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("✅ Telegram 消息发送成功！")
        else:
            print(f"❌ 发送失败: {res.status_code}, {res.text}")
    except Exception as e:
        print(f"❌ 发送异常: {e}")

def check_stock_exact(url):
    """通过页面核心元素精准判断有货/缺货"""
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            print(f"⚠️ 网页打不开 [HTTP {res.status_code}]: {url}")
            return False, "未知商品"

        soup = BeautifulSoup(res.text, "html.parser")
        
        # 1. 抓取商品标题
        title_tag = soup.find("h1") or soup.find("title")
        title = title_tag.get_text().strip() if title_tag else url

        # 2. 核心特征过滤：判断是否缺货
        page_html_lower = res.text.lower()
        
        # 查找购买按钮（EasyStore 常见的购买/购物车按钮标识）
        cart_button = soup.find("button", {"name": "add"}) or soup.find("button", class_=lambda c: c and "add-to-cart" in c)
        
        # 检查页面或按钮上是否有 Sold Out 关键字
        is_sold_out = False
        if cart_button:
            button_text = cart_button.get_text().lower()
            if "sold out" in button_text or "out of stock" in button_text or "disabled" in cart_button.attrs:
                is_sold_out = True
        else:
            # 如果压根没有购物车按钮，或者包含明显缺货文本
            if "sold out" in page_html_lower or "out of stock" in page_html_lower or "售罄" in page_html_lower:
                is_sold_out = True

        return not is_sold_out, title

    except Exception as e:
        print(f"❌ 解析异常 [{url}]: {e}")
        return False, "解析失败"

def main():
    print("🚀 开始逐个检测 17 个重点商品的真实网页状态...")
    vip_hits = []

    for code, url in VIP_ITEMS.items():
        is_in_stock, title = check_stock_exact(url)
        
        if is_in_stock:
            print(f"🔥 [检测到有货!] {code} -> {title}")
            vip_hits.append({"code": code, "title": title, "url": url})
        else:
            print(f"🔴 [缺货] {code}")

    if vip_hits:
        msg = "🚨<b>【重点关注型号返货/有货！】</b>\n\n"
        for item in vip_hits:
            msg += f"📦 <b>{item['code']}</b>\n"
            msg += f"📝 {item['title']}\n"
            msg += f"🔗 <a href='{item['url']}'>点击直接购买</a>\n\n"
        send_telegram_msg(msg)
    else:
        print("\n✅ 检测完成，目前 17 个重点商品均显示缺货。")

if __name__ == "__main__":
    main()
