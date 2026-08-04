import os
import re
import sys
import requests
from bs4 import BeautifulSoup

# ==================== 1. 配置参数 ====================

# 从环境变量读取 Telegram 参数
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")

# 需要监控的分类列表页
CATEGORY_URLS = [
    "https://kelabgasingbeyblade.my/beyblade-x?category_id=1&page=1",
    "https://kelabgasingbeyblade.my/beyblade-x?category_id=1&page=2",
    "https://kelabgasingbeyblade.my/beyblade-x?category_id=1&page=3"
]

# 你重点关注的型号列表及对应链接（用于精准匹配与高亮提醒）
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

# ==================== 2. 发送 Telegram 消息函数 ====================

def send_telegram_msg(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ 错误: 未设置 BOT_TOKEN 或 CHAT_ID 环境变量！")
        return False
    
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
            return True
        else:
            print(f"❌ Telegram 发送失败，状态码: {res.status_code}, 返回: {res.text}")
            return False
    except Exception as e:
        print(f"❌ 发送 Telegram 异常: {e}")
        return False

# ==================== 3. 检查重点商品单页逻辑 ====================

def check_vip_direct_pages():
    print("\n🔍 --- 正在直接检测 17 个重点关注商品的独立页面 ---")
    in_stock_vip = []

    for model_code, product_url in VIP_ITEMS.items():
        try:
            res = requests.get(product_url, headers=HEADERS, timeout=10)
            if res.status_code != 200:
                print(f"⚠️ 访问页面失败 [{model_code}]: HTTP {res.status_code}")
                continue

            soup = BeautifulSoup(res.text, "html.parser")
            page_text = soup.get_text().lower()

            # 判断是否有货逻辑：如果不含 out of stock 且包含 buy/cart 按钮相关文字，判定为有货
            # 兼容 Easystore/Shopify 常用结构
            is_out_of_stock = "out of stock" in page_text or "sold out" in page_text or "售罄" in page_text
            
            # 找到标题
            title_tag = soup.find("h1") or soup.find("title")
            title = title_tag.get_text().strip() if title_tag else model_code

            if not is_out_of_stock:
                print(f"🔥 [重点返货!] {model_code} - {title}")
                in_stock_vip.append({
                    "code": model_code,
                    "title": title,
                    "url": product_url
                })
            else:
                print(f"⚪ [{model_code}] 目前无货")
        except Exception as e:
            print(f"⚠️ 检测 [{model_code}] 异常: {e}")

    return in_stock_vip

# ==================== 4. 检查 3 个列表页全量商品 ====================

def check_category_pages():
    print("\n🔍 --- 正在检测 3 个分类列表页的全量商品 ---")
    in_stock_general = []

    for page_url in CATEGORY_URLS:
        print(f"\n正在抓取: {page_url}")
        try:
            res = requests.get(page_url, headers=HEADERS, timeout=10)
            if res.status_code != 200:
                print(f"⚠️ 抓取列表页失败: HTTP {res.status_code}")
                continue

            soup = BeautifulSoup(res.text, "html.parser")
            
            # 尝试匹配商品卡片容器（Easystore 常用 class）
            products = soup.find_all("div", class_=re.compile(r"product-item|grid-item|card", re.I))
            if not products:
                # 备用选择器：寻找包含商品链接的区块
                products = soup.find_all("a", href=re.compile(r"/products/"))

            print(f"在页面中搜寻到 {len(products)} 个商品元素")

            for item in products:
                item_text = item.get_text()
                
                # 如果明确含有 Sold out / Out of stock 说明无货
                if "sold out" in item_text.lower() or "out of stock" in item_text.lower():
                    continue

                # 提取链接与标题
                link_tag = item if item.name == "a" else item.find("a", href=re.compile(r"/products/"))
                if not link_tag:
                    continue

                href = link_tag.get("href", "")
                if not href.startswith("http"):
                    full_url = f"https://kelabgasingbeyblade.my{href}"
                else:
                    full_url = href

                title = link_tag.get_text().strip() or "Beyblade Product"

                # 排除重复的纯图片无文本标签
                if len(title) < 2:
                    continue

                in_stock_general.append({
                    "title": title,
                    "url": full_url
                })

        except Exception as e:
            print(f"⚠️ 抓取列表页异常: {e}")

    return in_stock_general

# ==================== 5. 主程序入口 ====================

def main():
    print("🚀 开始运行 Kelab Gasing Beyblade 库存监控程序...")

    # 1. 检测重点型号单页
    vip_hits = check_vip_direct_pages()

    # 2. 检测分类列表页
    general_hits = check_category_pages()

    # 汇总通知消息
    messages = []

    # 优先发送重点型号通知
    if vip_hits:
        msg = "🚨<b>【重点关注型号返货！】</b>\n\n"
        for item in vip_hits:
            msg += f"📦 <b>{item['code']}</b>\n"
            msg += f"🔗 <a href='{item['url']}'>点击直接购买商品</a>\n\n"
        messages.append(msg)

    # 发送普通全员补货通知
    if general_hits:
        # 去重
        seen_urls = set(item['url'] for item in vip_hits)
        unique_general = []
        for g in general_hits:
            if g['url'] not in seen_urls:
                seen_urls.add(g['url'])
                unique_general.append(g)

        if unique_general:
            msg = "📢<b>【页面发现有货/补货商品！】</b>\n\n"
            for item in unique_general[:10]:  # 限制单次推送最多 10 个，防止消息过长
                # 检查是否匹配重点编号
                is_vip_title = any(code in item['title'].upper() for code in VIP_ITEMS.keys())
                tag = "🔥 [重点型号]" if is_vip_title else "✨ [普通商品]"
                msg += f"{tag} {item['title']}\n"
                msg += f"🔗 <a href='{item['url']}'>点击查看</a>\n\n"
            messages.append(msg)

    # 执行发送
    if messages:
        for m in messages:
            send_telegram_msg(m)
    else:
        print("\n✅ 所有监控页面检测完毕，目前没有检测到新补货商品。")

if __name__ == "__main__":
    main()
