import os
import requests
import json
import re

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")

STATE_FILE = "stock_state.json"

VIP_ITEMS = {
    "BX-01": "https://kelabgasingbeyblade.my/products/bx-01-dran-sword-3-60f",
    "BX-34": "https://kelabgasingbeyblade.my/products/bx-34-cobalt-dragoon-2-60c",
    "BX-45": "https://kelabgasingbeyblade.my/products/bx-45-booster-samurai-calibur-6-70m",
    "BX-49": "https://kelabgasingbeyblade.my/products/bx-49-dran-strike-4-50ff",
    "BX-50": "https://kelabgasingbeyblade.my/products/bx-50-random-booster-vol11",
    "BXG-09": "https://kelabgasingbeyblade.my/products/bxg-09-cobalt-dragoon-2-60c",
    "CX-01": "https://kelabgasingbeyblade.my/products/cx-01-dran-brave-s6-60v",
    "CX-11": "https://kelabgasingbeyblade.my/products/cx-11-emperor-might-deck-set",
    "CX-12": "https://kelabgasingbeyblade.my/products/cx-12-phoenix-flare-z9-80ww",
    "CX-13": "https://kelabgasingbeyblade.my/products/cx-13-bahamutblitz-bk1-50i",
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

def load_previous_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_current_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ 保存状态失败: {e}")

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

def check_html_stock(url):
    """直接解析 HTML 页面内容，判断真正的库存"""
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return False, "页面打不开"

        html_text = res.text
        
        # 获取标题
        title_match = re.search(r'<title>(.*?)</title>', html_text, re.IGNORECASE)
        title = title_match.group(1).split('|')[0].strip() if title_match else url

        # 判断缺货的关键文本
        is_sold_out = False
        html_lower = html_text.lower()
        
        if "sold out" in html_lower or "out of stock" in html_lower or "售罄" in html_lower:
            is_sold_out = True
            
        # 只要没有明显 sold out，且页面包含 Add to Cart 相关的按钮或表单，即算有货
        if not is_sold_out:
            return True, title
            
        return False, title

    except Exception as e:
        print(f"❌ 抓取网页异常 [{url}]: {e}")
        return False, "解析失败"

def main():
    print("🚀 开始通过 HTML 实时抓取库存...")
    previous_state = load_previous_state()
    current_state = {}
    
    new_vip_restocks = []

    # 1. 逐个抓取 19 个型号
    for code, url in VIP_ITEMS.items():
        is_in_stock, title = check_html_stock(url)
        current_state[url] = is_in_stock
        
        was_in_stock = previous_state.get(url, False)

        if is_in_stock:
            print(f"🔥 [真实有货!] {code} - {title}")
            # 只要之前记录是 False (或者全新的商品)，就触发提醒
            if not was_in_stock:
                new_vip_restocks.append({"code": code, "title": title, "url": url})
        else:
            print(f"🔴 [缺货] {code}")

    # 2. 发送通知
    if new_vip_restocks:
        msg = "🚨<b>【重点关注型号返货/有货！】</b>\n\n"
        for item in new_vip_restocks:
            msg += f"📦 <b>{item['code']}</b> - {item['title']}\n"
            msg += f"🔗 <a href='{item['url']}'>点击直接购买</a>\n\n"
        send_telegram_msg(msg)
    else:
        print("\n✅ 检测完成，无新有货商品。")

    # 3. 保存新状态
    save_current_state(current_state)

if __name__ == "__main__":
    main()
