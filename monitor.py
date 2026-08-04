import os
import requests
from bs4 import BeautifulSoup

# 从环境变量读取 Telegram 参数
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")

# 你重点关注的 17 个商品链接
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
        print("❌ 错误: 未设置 BOT_TOKEN 或 CHAT_ID 环境变量！")
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
            print(f"❌ Telegram 发送失败: {res.status_code}, {res.text}")
    except Exception as e:
        print(f"❌ 发送异常: {e}")

def check_single_product_js(url):
    """访问 EasyStore 单品页后缀 .js，直接获取官方 JSON 数据判断库存"""
    try:
        json_url = f"{url}.js"
        res = requests.get(json_url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            data = res.json()
            # 只要有任何变体 (variant) 显示 available 为 True，就是有货
            is_available = data.get("available", False)
            title = data.get("title", "")
            return is_available, title
    except Exception as e:
        pass
    
    # 备用普通抓取逻辑
    try:
        res = requests.get(url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            page_text = soup.get_text().lower()
            is_out = "sold out" in page_text or "out of stock" in page_text or "售罄" in page_text
            title_tag = soup.find("h1") or soup.find("title")
            title = title_tag.get_text().strip() if title_tag else ""
            return not is_out, title
    except Exception:
        pass
    return False, ""

def main():
    print("🚀 开始进行精确库存扫描...")
    vip_hits = []

    # 1. 精确检测 17 个重点型号
    print("\n--- 正在检测 17 个重点型号库存 ---")
    for code, url in VIP_ITEMS.items():
        is_in_stock, title = check_single_product_js(url)
        if is_in_stock:
            print(f"🔥 [重点有货!] {code} - {title or url}")
            vip_hits.append({"code": code, "title": title or code, "url": url})
        else:
            print(f"🔴 [缺货] {code}")

    # 2. 抓取分类页上的其他有货商品
    print("\n--- 正在扫描分类页 ---")
    general_hits = []
    for cat_url in CATEGORY_URLS:
        try:
            res = requests.get(cat_url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                # 寻找所有商品链接
                links = soup.find_all("a", href=True)
                for a in links:
                    href = a["href"]
                    if "/products/" in href:
                        full_url = href if href.startswith("http") else f"https://kelabgasingbeyblade.my{href}"
                        # 避免重复检测重点型号
                        if any(v_url in full_url for v_url in VIP_ITEMS.values()):
                            continue
                        
                        # 检查父容器是否包含 sold out
                        parent_text = a.parent.parent.get_text().lower() if a.parent and a.parent.parent else ""
                        if "sold out" not in parent_text and "out of stock" not in parent_text:
                            text = a.get_text().strip()
                            if len(text) > 3 and "quick" not in text.lower():
                                general_hits.append({"title": text, "url": full_url})
        except Exception as e:
            print(f"⚠️ 抓取分类页异常: {e}")

    # 3. 组装并发送 Telegram 消息
    messages = []

    if vip_hits:
        msg = "🚨<b>【重点关注型号返货/有货！】</b>\n\n"
        for item in vip_hits:
            msg += f"📦 <b>{item['code']}</b> - {item['title']}\n"
            msg += f"🔗 <a href='{item['url']}'>点击直接购买</a>\n\n"
        messages.append(msg)

    # 去重处理分类页商品
    if general_hits:
        seen = set()
        unique_general = []
        for g in general_hits:
            if g['url'] not in seen:
                seen.add(g['url'])
                unique_general.append(g)

        if unique_general:
            msg = "📢<b>【页面发现其他有货商品】</b>\n\n"
            for item in unique_general[:6]:  # 最多推送6个
                msg += f"✨ {item['title']}\n"
                msg += f"🔗 <a href='{item['url']}'>点击查看</a>\n\n"
            messages.append(msg)

    if messages:
        for m in messages:
            send_telegram_msg(m)
    else:
        print("\n✅ 检测完成，当前重点商品无货。")

if __name__ == "__main__":
    main()
