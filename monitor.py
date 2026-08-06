import os
import requests
import json
import re
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")

STATE_FILE = "stock_state.json"

# 1. 19 个重点关注型号
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

# 2. 监控的 3 个分类页
CATEGORY_URLS = [
    "https://kelabgasingbeyblade.my/beyblade-x?category_id=1&page=1",
    "https://kelabgasingbeyblade.my/beyblade-x?category_id=1&page=2",
    "https://kelabgasingbeyblade.my/beyblade-x?category_id=1&page=3"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
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
    """检测 VIP 重点商品状态"""
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return False, "页面打不开"

        html_text = res.text
        title_match = re.search(r'<title>(.*?)</title>', html_text, re.IGNORECASE)
        title = title_match.group(1).split('|')[0].strip() if title_match else url

        html_lower = html_text.lower()
        if "sold out" in html_lower or "out of stock" in html_lower or "售罄" in html_lower:
            return False, title
        return True, title
    except Exception as e:
        print(f"❌ 抓取网页异常 [{url}]: {e}")
        return False, "解析失败"

def scan_category_pages():
    """扫描分类页上的所有其他商品"""
    print("\n🔍 --- 开始扫描 3 个分类页的其他商品 ---")
    category_products = {}
    
    for page_url in CATEGORY_URLS:
        try:
            res = requests.get(page_url, headers=HEADERS, timeout=10)
            if res.status_code != 200:
                continue

            soup = BeautifulSoup(res.text, "html.parser")
            # 找到所有包含商品链接的元素
            links = soup.find_all("a", href=lambda h: h and "/products/" in h)
            
            for link in links:
                href = link["href"]
                full_url = href if href.startswith("http") else f"https://kelabgasingbeyblade.my{href}"
                
                # 过滤掉 VIP 重点商品（VIP 单独精确监测）
                if any(v_url in full_url for v_url in VIP_ITEMS.values()):
                    continue

                # 向上寻找商品卡片父节点判断缺货状态
                parent = link.find_parent(["div", "li", "article"])
                card_text = parent.get_text().lower() if parent else ""
                
                is_sold_out = "sold out" in card_text or "out of stock" in card_text or "售罄" in card_text
                title = link.get_text().strip() or "分类页商品"
                
                if len(title) > 3 and "quick" not in title.lower():
                    category_products[full_url] = {
                        "in_stock": not is_sold_out,
                        "title": title
                    }
        except Exception as e:
            print(f"⚠️ 扫描分类页失败 [{page_url}]: {e}")

    return category_products

def main():
    print("🚀 开始全量综合库存检测（重点型号 + 分类页）...")
    previous_state = load_previous_state()
    current_state = {}
    
    new_vip_restocks = []
    new_general_restocks = []

    # 1. 检测 19 个 VIP 重点型号
    print("\n🔍 --- 正在检测 VIP 重点型号 ---")
    for code, url in VIP_ITEMS.items():
        is_in_stock, title = check_html_stock(url)
        current_state[url] = is_in_stock
        was_in_stock = previous_state.get(url, False)

        if is_in_stock:
            print(f"🔥 [重点有货] {code} - {title}")
            if not was_in_stock:
                new_vip_restocks.append({"code": code, "title": title, "url": url})
        else:
            print(f"🔴 [缺货] {code}")

    # 2. 扫描 3 个分类页
    cat_items = scan_category_pages()
    for full_url, item in cat_items.items():
        is_in_stock = item["in_stock"]
        title = item["title"]
        current_state[full_url] = is_in_stock
        was_in_stock = previous_state.get(full_url, False)

        if is_in_stock:
            print(f"✨ [分类页有货] {title}")
            if not was_in_stock:
                new_general_restocks.append({"title": title, "url": full_url})

    # 3. 发送提醒
    if new_vip_restocks:
        msg = "🚨<b>【重点关注型号刚补货！】</b>\n\n"
        for item in new_vip_restocks:
            msg += f"📦 <b>{item['code']}</b>\n"
            msg += f"📝 {item['title']}\n"
            msg += f"🔗 <a href='{item['url']}'>点击直接购买</a>\n\n"
        send_telegram_msg(msg)

    if new_general_restocks:
        msg = "📢<b>【分类页发现新补货商品！】</b>\n\n"
        for item in new_general_restocks[:6]:
            msg += f"✨ {item['title']}\n"
            msg += f"🔗 <a href='{item['url']}'>点击查看</a>\n\n"
        send_telegram_msg(msg)

    if not new_vip_restocks and not new_general_restocks:
        print("\n✅ 检测完成，全盘暂无新补货商品。")

    save_current_state(current_state)

if __name__ == "__main__":
    main()
