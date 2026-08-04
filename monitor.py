import os
import requests

# 从环境变量读取 Telegram 参数
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")

# 17 个重点关注商品（商品 handle 路径）
VIP_ITEMS = {
    "BX-34": "bx-34-cobalt-dragoon-2-60c",
    "BX-45": "bx-45-booster-samurai-calibur-6-70m",
    "BX-49": "bx-49-dran-strike-4-50ff",
    "BX-50": "bx-50-random-booster-vol11",
    "BXG-09": "bxg-09-cobalt-dragoon-2-60c",
    "CX-01": "cx-01-dran-brave-s6-60v",
    "CX-11": "cx-11-emperor-might-deck-set",
    "CX-12": "cx-12-phoenix-flare-z9-80ww",
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def send_telegram_msg(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ 错误: 未设置 BOT_TOKEN 或 CHAT_ID！")
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

def check_easystore_stock(handle):
    """严格通过 EasyStore 官方 JSON API 查询系统底层库存"""
    json_url = f"https://kelabgasingbeyblade.my/products/{handle}.js"
    try:
        res = requests.get(json_url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            data = res.json()
            
            # 严格检查 available 状态
            is_available = data.get("available", False)
            title = data.get("title", handle)

            # 进一步双重验证变体 (variants) 的 stock/quantity 状态
            variants = data.get("variants", [])
            has_variant_stock = any(v.get("available", False) for v in variants)

            if is_available and has_variant_stock:
                return True, title
            else:
                return False, title
    except Exception as e:
        print(f"⚠️ 解析 [{handle}] 接口异常: {e}")
    
    # 获取失败时，严格默认为 False (缺货)，宁可错过绝不误报
    return False, handle

def main():
    print("🚀 开始进行零误报的精确 API 库存检测...")
    vip_hits = []

    for code, handle in VIP_ITEMS.items():
        is_in_stock, title = check_easystore_stock(handle)
        full_url = f"https://kelabgasingbeyblade.my/products/{handle}"
        
        if is_in_stock:
            print(f"🔥 [确信有货!] {code} - {title}")
            vip_hits.append({"code": code, "title": title, "url": full_url})
        else:
            print(f"🔴 [缺货/售罄] {code}")

    if vip_hits:
        msg = "🚨<b>【重点关注型号返货/有货！】</b>\n\n"
        for item in vip_hits:
            msg += f"📦 <b>{item['code']}</b> - {item['title']}\n"
            msg += f"🔗 <a href='{item['url']}'>点击直接购买</a>\n\n"
        send_telegram_msg(msg)
    else:
        print("\n✅ 检测完成！17 个重点商品目前均处于缺货状态，没有发送 Telegram 干扰消息。")

if __name__ == "__main__":
    main()
