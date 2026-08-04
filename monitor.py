import os
import requests
from bs4 import BeautifulSoup

# 从环境变量读取 Telegram 参数
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")

# 17 个重点关注商品
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

# 监控的 3 个分类页面
CATEGORY_URLS = [
    "https://kelabgasingbeyblade.my/beyblade-x?category_id=1&page=1",
    "https://kelabgasingbeyblade.my/beyblade-x?category_id=1&page=2",
    "https://kelabgasingbeyblade.my/beyblade-x?category_id=1&page=3"
]

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

def check_vip_stock(url):
    """精准检测重点商品单页状态"""
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return False, "未知商品"

        soup = BeautifulSoup(res.text, "html.parser")
        title_tag = soup.find("h1") or soup.find("title")
        title = title_tag.get_text().strip() if title_tag else url

        # 检查购物车按钮与售罄关键字
        page_text = res.text.lower()
        cart_button = soup.find("button", {"name": "add"}) or soup.find("button", class_=lambda c: c and "add-to-cart" in c)
        
        is_sold_out = False
        if cart_button:
            button_text = cart_button.get_text().lower()
            if "sold out" in button_text or "out of stock" in button_text or "disabled" in cart_button.attrs:
                is_sold_out = True
        else:
            if "sold out" in page_text or "out of stock" in page_text or "售罄" in page_text:
                is_sold_out = True

        return not is_sold_out, title
    except Exception:
        return False, "解析失败"

def check_category_pages():
    """扫描分类页上的所有商品"""
    print("\n🔍 --- 开始扫描 3 个分类页的其他商品 ---")
    other_in_stock = []
    
    for page_url in CATEGORY_URLS:
        try:
            res = requests.get(page_url, headers=HEADERS, timeout=10)
            if res.status_code != 200:
                continue

            soup = BeautifulSoup(res.text, "html.parser")
            # 找到页面上所有的商品卡片/容器
            items = soup.find_all("div", class_=lambda c: c and ("product" in c or "grid" in c or "item" in c))
            
            for item in items:
                item_text = item.get_text().lower()
                # 排除缺货商品
                if "sold out" in item_text or "out of stock" in item_text or "售罄" in item_text:
                    continue

                link = item.find("a", href=lambda h: h and "/products/" in h)
                if not link:
                    continue

                href = link["href"]
                full_url = href if href.startswith("http") else f"https://kelabgasingbeyblade.my{href}"
                
                # 如果这个商品属于 17 个重点型号之一，则忽略（因为重点型号由 VIP 逻辑单独汇报）
                if any(v_url in full_url for v_url in VIP_ITEMS.values()):
                    continue

                title = link.get_text().strip()
                if len(title) > 3 and "quick" not in title.lower():
                    other_in_stock.append({"title": title, "url": full_url})
        except Exception as e:
            print(f"⚠️ 分类页扫描异常: {e}")

    return other_in_stock

def main():
    print("🚀 开始进行综合库存检测...")
    vip_hits = []

    # 1. 检测 17 个重点商品
    print("🔍 --- 正在检测 17 个重点型号 ---")
    for code, url in VIP_ITEMS.items():
        is_in_stock, title = check_vip_stock(url)
        if is_in_stock:
            print(f"🔥 [重点有货!] {code} -> {title}")
            vip_hits.append({"code": code, "title": title, "url": url})
        else:
            print(f"🔴 [缺货] {code}")

    # 2. 检测分类页其他商品
    general_hits = check_category_pages()

    # 3. 组装并发送 Telegram 通知
    messages = []

    if vip_hits:
        msg = "🚨<b>【重点关注型号返货/有货！】</b>\n\n"
        for item in vip_hits:
            msg += f"📦 <b>{item['code']}</b>\n"
            msg += f"📝 {item['title']}\n"
            msg += f"🔗 <a href='{item['url']}'>点击直接购买</a>\n\n"
        messages.append(msg)

    if general_hits:
        # 去重
        seen = set()
        unique_general = []
        for g in general_hits:
            if g['url'] not in seen:
                seen.add(g['url'])
                unique_general.append(g)

        if unique_general:
            msg = "📢<b>【分类页发现其他补货商品】</b>\n\n"
            for item in unique_general[:6]:  # 单次最多展示前 6 个
                msg += f"✨ {item['title']}\n"
                msg += f"🔗 <a href='{item['url']}'>点击查看</a>\n\n"
            messages.append(msg)

    if messages:
        for m in messages:
            send_telegram_msg(m)
    else:
        print("\n✅ 全盘检测完成，当前重点型号与分类页均无新补货。")

if __name__ == "__main__":
    main()
