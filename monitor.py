import os
import requests
import json

# 从环境变量读取 Telegram 参数
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")

STATE_FILE = "stock_state.json"

# 重点关注商品 (Model Code -> Handle)
VIP_ITEMS = {
    "BX-01": "bx-01-dran-sword-3-60f",
    "BX-34": "bx-34-cobalt-dragoon-2-60c",
    "BX-45": "bx-45-booster-samurai-calibur-6-70m",
    "BX-49": "bx-49-dran-strike-4-50ff",
    "BX-50": "bx-50-random-booster-vol11",
    "BXG-09": "bxg-09-cobalt-dragoon-2-60c",
    "CX-01": "cx-01-dran-brave-s6-60v",
    "CX-11": "cx-11-emperor-might-deck-set",
    "CX-12": "cx-12-phoenix-flare-z9-80ww",
    "CX-13": "cx-13-bahamutblitz-bk1-50i",
    "CX-14": "cx-14-knightfortress-gv8-70un",
    "CX-18": "cx-18-brachio-whip-select",
    "UX-01": "ux-01-dran-buster-1-60a",
    "UX-03": "ux-03-wizard-rod-5-70b",
    "UX-06": "ux-06-leon-crest-7-60gn",
    "UX-11": "ux-11-impact-drake-9-60lr",
    "UX-13": "ux-13-golem-rock-1-60un",
    "UX-15": "ux-15-shark-scale-deck-set",
    "UX-17": "ux-17-meteor-dragoon-3-70j"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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

def check_single_product_api(handle):
    """直接调取 EasyStore 底层 JSON API，100% 准确获取库存和标题"""
    url = f"https://kelabgasingbeyblade.my/products/{handle}.js"
    try:
        res = requests.get(url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            data = res.json()
            is_available = data.get("available", False)
            title = data.get("title", handle)
            return is_available, title
    except Exception:
        pass
    return False, handle

def main():
    print("🚀 开始极速全量库存检测...")
    previous_state = load_previous_state()
    current_state = {}
    
    new_vip_restocks = []
    new_general_restocks = []

    # 1. 扫描 17 个重点型号
    print("\n🔍 --- 正在扫描重点关注型号 ---")
    for code, handle in VIP_ITEMS.items():
        full_url = f"https://kelabgasingbeyblade.my/products/{handle}"
        is_in_stock, title = check_single_product_api(handle)
        
        current_state[full_url] = is_in_stock
        was_in_stock = previous_state.get(full_url, False)

        if is_in_stock:
            print(f"🔥 [有货] {code} - {title}")
            # 只有从“无货”变成“有货”或者首次运行检测到有货，才触发通知
            if not was_in_stock:
                new_vip_restocks.append({"code": code, "title": title, "url": full_url})
        else:
            print(f"🔴 [缺货] {code}")

    # 2. 扫描 3 个分类页的所有商品 (使用 API 通道)
    print("\n🔍 --- 正在扫描 3 个分类页的所有商品 ---")
    for page in [1, 2, 3]:
        cat_url = f"https://kelabgasingbeyblade.my/collections/beyblade-x/products.json?page={page}&limit=50"
        try:
            res = requests.get(cat_url, headers=HEADERS, timeout=8)
            if res.status_code == 200:
                products = res.json().get("products", [])
                for p in products:
                    handle = p.get("handle")
                    full_url = f"https://kelabgasingbeyblade.my/products/{handle}"
                    title = p.get("title", "")
                    
                    # 跳过重点型号（已经单独监测）
                    if handle in VIP_ITEMS.values():
                        continue
                    
                    # 检查是否有任何变体有库存
                    is_available = any(v.get("available", False) for v in p.get("variants", []))
                    current_state[full_url] = is_available
                    was_in_stock = previous_state.get(full_url, False)

                    if is_available:
                        if not was_in_stock:
                            new_general_restocks.append({"title": title, "url": full_url})
        except Exception as e:
            print(f"⚠️ 分类页 Page {page} 抓取失败: {e}")

    # 3. 发送新补货通知
    if new_vip_restocks:
        msg = "🚨<b>【重点关注型号刚补货！】</b>\n\n"
        for item in new_vip_restocks:
            msg += f"📦 <b>{item['code']}</b>\n"
            msg += f"📝 {item['title']}\n"
            msg += f"🔗 <a href='{item['url']}'>立即抢购</a>\n\n"
        send_telegram_msg(msg)

    if new_general_restocks:
        msg = "📢<b>【分类页发现新补货商品！】</b>\n\n"
        for item in new_general_restocks[:6]:
            msg += f"✨ {item['title']}\n"
            msg += f"🔗 <a href='{item['url']}'>点击查看</a>\n\n"
        send_telegram_msg(msg)

    if not new_vip_restocks and not new_general_restocks:
        print("\n✅ 检测完成：没有发现“新补货”的商品。")

    # 保存本次检测状态
    save_current_state(current_state)

if __name__ == "__main__":
    main()
