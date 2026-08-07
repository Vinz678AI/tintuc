#!/usr/bin/env python3
"""
Telegram News Bot - Persistent Duplicate Prevention
Saves sent IDs to GitHub Gist/Release for persistence across runs
"""

import requests
import json
import os
import sys
from datetime import datetime

BOT_TOKEN = "8892609299:AAF_9n9XgGuAXZD-nZ8Rl0vIzXSJ_mS2Qd8"
CHAT_ID = "5439095079"
SENT_FILE = "sent_news_ids.json"
GIST_ID = None  # Set your gist ID here for persistent storage
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')  # From GitHub Actions secrets


def load_ids_from_gist():
    """Load sent IDs from GitHub Gist (persistent storage)"""
    if not GIST_ID or not GITHUB_TOKEN:
        return load_local_ids()
    
    try:
        url = f"https://api.github.com/gists/{GIST_ID}"
        resp = requests.get(url, headers={"Authorization": f"Bearer {GITHUB_TOKEN}"})
        if resp.ok:
            data = resp.json()
            for filename, content in data.get('files', {}).items():
                if filename == 'sent_ids.json':
                    return set(json.loads(content['content']))
    except Exception as e:
        print(f"Error loading from gist: {e}")
    
    return load_local_ids()


def save_ids_to_gist(ids):
    """Save sent IDs to GitHub Gist (persistent storage)"""
    if not GIST_ID or not GITHUB_TOKEN:
        return save_local_ids(ids)
    
    try:
        url = f"https://api.github.com/gists/{GIST_ID}"
        payload = {
            "files": {
                "sent_ids.json": {
                    "content": json.dumps(list(ids), indent=2)
                }
            }
        }
        resp = requests.patch(url, 
                             headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
                             json=payload)
        if resp.ok:
            print("✅ Sent IDs saved to GitHub Gist")
        else:
            print(f"❌ Failed to save to gist: {resp.text}")
    except Exception as e:
        print(f"Error saving to gist: {e}")
    
    return save_local_ids(ids)


def load_local_ids():
    """Load from local file"""
    try:
        with open(SENT_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_local_ids(ids):
    """Save to local file"""
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        json.dump(list(ids), f, indent=2)


def get_updates(offset=0):
    """Get updates from Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}"
    try:
        resp = requests.get(url, timeout=30)
        if resp.ok:
            data = resp.json()
            if data.get('ok'):
                return data['result']
    except Exception as e:
        print(f"Error: {e}")
    return []


def send_message(text):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    
    success = True
    for i, chunk in enumerate(chunks):
        payload = {"chat_id": CHAT_ID, "text": chunk, "parse_mode": "Markdown"}
        try:
            r = requests.post(url, json=payload, timeout=30)
            if not r.json().get('ok'):
                print(f"❌ Chunk {i} failed: {r.text}")
                success = False
            else:
                print(f"✅ Chunk {i} sent")
        except Exception as e:
            print(f"❌ Error: {e}")
            success = False
    return success


def build_news():
    """Build daily news content"""
    today = datetime.now().strftime("%d/%m/%Y")
    sent = load_ids_from_gist()
    
    def make_id(t, idx, link): return f"{t}_{idx}_{link}"
    
    def filter_items(items, sent_set):
        new_items = []
        for item in items:
            k = make_id(item[0], item[1], item[2])
            if k not in sent_set:
                new_items.append({"id": k, "title": item[3], "link": item[2]})
                sent_set.add(k)
        return new_items, sent_set
    
    # Vietnam news
    vn_data = [
        ("VN", 1, "https://thanhnien.vn/79-nam-ngay-thuong-binh-liet-si-2771947-2772026-chien-dich-dac-biet-giua-thoi-binh-185260726214212417.htm", "Ngày Thương binh - Liệt sĩ 27/7: Chiến dịch tìm kiếm hài cốt"),
        ("VN", 2, "https://www.bbc.com/vietnamese/articles/c8jne9k1vj9o", "Tàu Việt Nam chìm ở Biển Đông: 17 người mất tích"),
        ("VN", 3, "https://cafef.vn/sang-26-7-danh-dau-buoc-ngoat-lich-su-nganh-luyen-kim-viet-nam-dai-gia-bi-an-chi-18000-ty-dong-cham-dut-thoi-ky-chay-mau-bo-xit-188260726225418521.chn", "Lần đầu sản xuất nhôm thỏi thành công"),
        ("VN", 4, "https://www.vietnamplus.vn/thoi-tiet-ngay-277-nhieu-noi-nang-nong-chieu-toi-va-dem-co-mua-dong-dien-rong-post1126472.vnp", "Bão số 2 suy yếu, không ảnh hưởng Việt Nam"),
        ("VN", 5, "https://vietnamnet.vn/thoi-su", "Hà Nội lắp 20.000 camera AI"),
        ("VN", 6, "https://vnexpress.net/thoi-su", "Thủ tướng chỉ đạo vụ lật canô Phú Quốc"),
        ("VN", 7, "https://vietnamnet.vn/thoi-su", "Cháy lớn tại Hà Nội và TPHCM"),
        ("VN", 8, "https://doisongphapluat.com.vn/ngay-mai-27-7-xet-xu-ong-trum-vu-100-tan-thuc-pham-chuc-nang-gia-a728891.html", "Xét xử 'ông trùm' thực phẩm chức năng giả"),
        ("VN", 9, "https://thanhnien.vn/thoi-su.htm", "Triệt phá ổ lừa đảo tại TP.HCM"),
        ("VN", 10, "https://vietnamnet.vn/thoi-su", "Metro số 6 đề xuất 2 ga ngầm kết nối sân bay")
    ]
    
    # World news (20 items)
    world_data = [
        ("WORLD", 1, "https://apnews.com/article/iran-war-united-states-ceasefire-ad9fa27d5b1b5fd51e30d923ee738238", "Mỹ và Iran tạm ngừng tấn công tại Dubai"),
        ("WORLD", 2, "https://www.aljazeera.com/news/2026/7/26/new-front-in-us-iran-war-escalates-as-houthis-fire-at-saudi-oil-facilities", "Houthis tấn công Saudi Arabia"),
        ("WORLD", 3, "https://www.modernghana.com/amp/videonews/687505", "Giá dầu vượt 100 USD/thùng"),
        ("WORLD", 4, "https://www.bbc.com/news/world", "Nghi phạm Berlin Pride bị bắn chết"),
        ("WORLD", 5, "https://news.net/news/2-dead-in-ukraine-from-russian-attacks-4-more-in-russian-held-area-hit-by-ukrainian-drones/", "Ukraine: 2 người chết do tên lửa Nga"),
        ("WORLD", 6, "https://www.bbc.com/news/world", "Ấn Độ: Biểu tình sinh viên tan rã"),
        ("WORLD", 7, "https://news.net/northamerica/news/brazils-government-denies-visas-to-us-officials-over-upcoming-elections/", "Brazil từ chối thị thực quan chức Mỹ"),
        ("WORLD", 8, "https://www.bbc.com/news/world", "ICC cách chức Tổng prosecute"),
        ("WORLD", 9, "https://www.bbc.com/news/world", "Israel tiếp tục raids ở Bờ Tây"),
        ("WORLD", 10, "https://www.bbc.com/news/world", "Cháy rừng Pháp-Tây Ban Nha: 330.000 người sơ tán"),
        ("WORLD", 11, "https://www.bbc.com/news/world", "Anh cam kết hỗ trợ Ukraine"),
        ("WORLD", 12, "https://www.bbc.com/news/world", "Trump chỉ trích báo chí"),
        ("WORLD", 13, "https://www.bbc.com/news/world", "Meghan Markle xuất hiện MasterChef"),
        ("WORLD", 14, "https://www.newser.com/article/4c578fc74746052627b1c87845fdc0d5/", "Pentagon xóa 4 binh sĩ tử vong"),
        ("WORLD", 15, "https://notesfrompoland.com/2026/07/22/germany-deploys-soldiers-to-poland-to-help-reinforce-eastern-borders", "Đức điều quân giúp Ba Lan"),
        ("WORLD", 16, "https://www.vietnam.vn/ba-lan-lien-tiep-chan-may-bay-quan-su-nga-tren-bien-baltic", "Ba Lan chặn máy bay quân sự Nga"),
        ("WORLD", 17, "https://www.bbc.com/news/world", "Nữ võ sĩ quyền anh Ấn Độ tranh huy chương"),
        ("WORLD", 18, "https://www.bbc.com/news/world", "Tòa nhà Flatiron NYC rao bán"),
        ("WORLD", 19, "https://www.bbc.com/news/world", "Nhà tù Cameroon phòng thu âm"),
        ("WORLD", 20, "https://www.bbc.com/news/world", "EU tranh luận về chính sách di cư")
    ]
    
    # Poland news (10 items)
    poland_data = [
        ("POLAND", 1, "https://www.visahq.news/2026-07-24/pl/poland-sets-new-record-for-migrant-deportations-in-first-half-of-2026/", "Kỷ lục trục xuất di dân: 5.640 người"),
        ("POLAND", 2, "https://y94.com/2026/07/22/poland-hungarys-foreign-worker-curbs-create-headache-for-business/", "Siết chặt lao động nước ngoài"),
        ("POLAND", 3, "https://industryalarm.eu/revolution-for-ukrainians-in-poland/a-test-to-pass-and-a-loyalty-pledge/to-sign/", "Luật quốc tịch mới: 8 năm cư trú"),
        ("POLAND", 4, "https://brusselssignal.eu/2026/07/poland-takes-control-of-illegal-border-crossings/in/the/east/leaves/backdoor/open/", "Giảm 98% nhập cư trái phép"),
        ("POLAND", 5, "https://brusselssignal.eu/2026/07/poland-takes-control-of-illegal-border-crossings/in/the/east/leaves/backdoor/open/", "20.000+ giấy phép lao động châu Phi"),
        ("POLAND", 6, "https://www.vov.vn/quan-su-quoc-phong/ba-lan-khoi-dong-chuong-trinh-doi-moi-quoc-phong-205-trieu-usd-post1318031.vov", "Ba Lan-Đức phối hợp East Shield"),
        ("POLAND", 7, "https://www.vietnam.vn/san-xuat-ten-lua-patriot-ba-lan-ngo-loi-voi-my-ukraine-mong-nhat-ban/chung-tay", "Đề nghị Mỹ đàm phán Patriot"),
        ("POLAND", 8, "https://www.vietnam.vn/tong-thong-ba-lan-bac-du-luat-mo-rong-quyen-cho-cac-cap-doi/khong-ket-hon", "Tổng thống Nawrocki phủ quyết"),
        ("POLAND", 9, "https://congluan.vn/ba-lan/truy-to/thanh-nien-ukraine/pha-hoai/dai-tuong-niem/kich-dong/thu-han/sac-toc/post353758.html", "Truy tố thanh niên Ukraine phá hoại"),
        ("POLAND", 10, "https://brusselssignal.eu/2026/07/poland-takes-control-of/illegall-border-crossings/in/the/east/leaves/backdoor/open/", "Căng thẳng cộng đồng Muslim tại Kraków")
    ]
    
    # Immigration priority (5 items)
    imm_data = [
        ("IMMIGRATION", 1, "https://www.visahq.news/2026-07-24/pl/poland-sets-new-record-for-migrant-deportations/in/first-half/of/2026/", "Kỷ lục trục xuất: 5.640 người (+28% YoY)"),
        ("IMMIGRATION", 2, "https://y94.com/2026/07/22/poland-hungarys/foreign-worker-curbs/create/headache/for/business/", "Siết chặt lao động: thiếu nhân công"),
        ("IMMIGRATION", 3, "https://industryalarm.eu/revolution-for-ukrainians-in/poland/a-test/to/pass-and/a-loyalty-pledge/to/sign/", "Luật quốc tịch mới: 3→8 năm"),
        ("IMMIGRATION", 4, "https://brusselssignal.eu/2026/07/poland-takes/control/of/illegal/border/crossings/in/the/east/leaves/backdoor/open/", "Biên giới an toàn: Giảm 98%"),
        ("IMMIGRATION", 5, "https://brusselssignal.eu/2026/07/poland-takes/control/of/illegal/border/crossings/in/the/east/leaves/backdoor/open/", "Lao động châu Phi: 20.000+ giấy phép")
    ]
    
    vn_new, sent = filter_items(vn_data, sent)
    world_new, sent = filter_items(world_data, sent)
    poland_new, sent = filter_items(poland_data, sent)
    imm_new, sent = filter_items(imm_data, sent)
    
    # Save to persistent storage
    save_ids_to_gist(sent)
    
    # Build output
    out = []
    out.append("*📰 TIN TỨC HÀNG NGÀY*")
    out.append(f"*📅 {today}*")
    out.append("")
    
    if vn_new:
        out.append(f"*🇻🇳 VIỆT NAM — {len(vn_new)} TIN MỚI*")
        for i, item in enumerate(vn_new[:10], 1):
            out.append(f"{i}. {item['title']}")
            out.append(f"   [🔗 Link]({item['link']})")
        out.append("")
    
    if world_new:
        out.append(f"*🌍 THẾ GIỚI — {len(world_new)} TIN MỚI*")
        for i, item in enumerate(world_new[:20], 1):
            out.append(f"{i}. {item['title']}")
            out.append(f"   [🔗 Link]({item['link']})")
        out.append("")
    
    if poland_new:
        out.append(f"*🇵🇱 BA LAN — {len(poland_new)} TIN MỚI*")
        for i, item in enumerate(poland_new[:10], 1):
            out.append(f"{i}. {item['title']}")
            out.append(f"   [🔗 Link]({item['link']})")
        out.append("")
    
    if imm_new:
        out.append("*🚨 5 TIN DI TRÚ BA LAN (Ưu tiên)*")
        for i, item in enumerate(imm_new[:5], 1):
            out.append(f"{i}. {item['title']}")
            out.append(f"   [🔗 Link]({item['link']})")
        out.append("")
    
    out.append("_🤖 Auto-generated by Telegram News Bot_")
    
    return "\n".join(out), len(vn_new) + len(world_new)


def main():
    print("🚀 Đang chuẩn bị tin tức...")
    content, count = build_news()
    print(f"📝 {len(content)} ký tự, {count} tin mới")
    
    if send_message(content):
        print("✅ Gửi thành công!")
    else:
        print("❌ Gửi thất bại!")
    
    log = f"news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(log, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"📁 Log: {log}")


if __name__ == "__main__":
    main()
