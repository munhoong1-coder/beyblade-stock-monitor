import os
import re
import requests

# 从环境变量读取 Telegram 参数
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")

# 重点关注的型号列表（自动匹配商品标题）
VIP_MODELS = [
    "BX-34", "BX-45", "BX-49", "BX-50", "BXG-09",
    "CX-01", "CX-11", "CX-12", "CX-14", "CX-18",
    "UX-01", "UX-03", "UX-06", "UX-11", "UX-13", "UX-15", "UX-17"
]

# 监控的分类页面 API/页面 URL
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
            print("✅ Telegram 通知已成功发送！")
        else:
            print(f"❌ 发送失败，HTTP {res.status_code}")
    except Exception as e:
        print(f"❌ 发送异常: {e}")

def monitor_stock():
    print("🚀 开始进行精确库存检测...")
    vip_in_stock = []
    normal_in_stock = []

    for url in CATEGORY_URLS:
        print(f"正在扫描: {url}")
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code != 200:
                print(f"⚠️ 页面加载失败: HTTP {res.status_code}")
                continue

            html = res.text

            # 通过正则精准提取 Easystore 平台的商品卡片块
            # 在 Easystore 中，带有 class="sold-out" 或包含 "Sold out" 文本的表示缺货
            # 找到包含商品信息的 HTML 块
            items = re.findall(r'<a[^>]+href="(/products/[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
            
            for href, content in items:
                # 清理标题内容
                clean_title = re.sub(r'<[^>]+>', ' ', content).strip()
                clean_title = ' '.join(clean_title.split())

                # 忽略过短或干扰文本
                if not clean_title or len(clean_title) < 4 or "quick add" in clean_title.lower():
                    continue

                full_url = f"https://kelabgasingbeyblade.my{href}"

                # 判断缺货关键字
                if "sold out" in content.lower() or "out of stock" in content.lower() or "售罄" in content:
                    print(f"🔴 [缺货] {clean_title}")
                    continue

                # 检查是否匹配重点型号
                is_vip = False
                matched_code = ""
                for code in VIP_MODELS:
                    if code.lower() in clean_title.lower():
                        is_vip = True
                        matched_code = code
                        break

                if is_vip:
                    print(f"🔥 [重点有货!] {clean_title}")
                    vip_in_stock.append({"code": matched_code, "title": clean_title, "url": full_url})
                else:
                    print(f"🟢 [普通有货] {clean_title}")
                    normal_in_stock.append({"title": clean_title, "url": full_url})

        except Exception as e:
            print(f"⚠️ 解析错误: {e}")

    # 发送通知逻辑
    if vip_in_stock:
        # 去重
        seen = set()
        msg = "🚨<b>【重点关注型号返货！】</b>\n\n"
        for item in vip_in_stock:
            if item['url'] not in seen:
                seen.add(item['url'])
                msg += f"📦 <b>{item['code']}</b> - {item['title']}\n"
                msg += f"🔗 <a href='{item['url']}'>点击直接购买</a>\n\n"
        send_telegram_msg(msg)

    if normal_in_stock:
        seen = set(x['url'] for x in vip_in_stock)
        unique_normals = [n for n in normal_in_stock if n['url'] not in seen and not seen.add(n['url'])]
        
        if unique_normals:
            msg = "📢<b>【其他上架/补货商品】</b>\n\n"
            for item in unique_normals[:8]:  # 推送前8个
                msg += f"✨ {item['title']}\n"
                msg += f"🔗 <a href='{item['url']}'>点击查看商品</a>\n\n"
            send_telegram_msg(msg)

    if not vip_in_stock and not normal_in_stock:
        print("\n✅ 检测完成，当前没有任何新补货/有货商品。")

if __name__ == "__main__":
    monitor_stock()
