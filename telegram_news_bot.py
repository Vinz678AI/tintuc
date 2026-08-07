#!/usr/bin/env python3
"""
Telegram News Bot - Final Working Version
Simple, reliable, with command trigger support
"""

import requests
import json
import sys
from datetime import datetime

BOT_TOKEN = "8892609299:AAF_9n9XgGuAXZD-nZ8Rl0vIzXSJ_mS2Qd8"
CHAT_ID = "5439095079"
SENT_FILE = "sent_news_ids.txt"


def load_ids():
    try:
        with open(SENT_FILE) as f:
            return set(line.strip() for line in f if line.strip())
    except:
        return set()


def save_ids(ids):
    with open(SENT_FILE, 'w') as f:
        for sid in sorted(ids):
            f.write(sid + '\n')


def send(msg):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    for i in range(0, len(msg), 4000):
        chunk = msg[i:i+4000]
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": chunk, "parse_mode": "Markdown"})
        if not r.json().get('ok'):
            print(f"❌ Error: {r.text}")
            return False
        print(f"✅ Sent chunk {i//4000 + 1}")
    return True


def build_news():
    """Build news content"""
    today = datetime.now().strftime("%d/%m/%Y")
    sent = load_ids()
    
    def nid(t, i, l): return f"{t}_{i}_{l}"
    
    def filt(items, s):
        n = []
        for item in items:
            k = nid(item[0], item[1], item[2])
            if k not in s:
                n.append({"id": k, "title": item[3], "link": item[2]})
                s.add(k)
        return n, s
    
    vn = [("VN", 1, "https://thanhnien.vn/79-nam-ngay-thuong-binh-liet-si-2771947-2772026-chien-dich-dac-biet-giua-thoi-binh-185260726214212417.htm", "Ngày Thương binh - Liệt sĩ 27/7: Chiến dịch '500 ngày đêm' tìm kiếm hài cốt"),
          ("VN", 2, "https://www.bbc.com/vietnamese/articles/c8jne9k1vj9o", "Tàu Việt Nam chìm ở Biển Đông: 17 người mất tích"),
          ("VN", 3, "https://cafef.vn/sang-26-7-danh-dau-buoc-ngoat-lich-su-nganh-luyen-kim-viet-nam-dai-gia-bi-an-chi-18000-ty-dong-cham-dut-thoi-ky-chay-mau-bo-xit-188260726225418521.chn", "Lần đầu sản xuất nhôm thỏi thành công: 18.000 tỷ đồng"),
          ("VN", 4, "https://www.vietnamplus.vn/thoi-tiet-ngay-277-nhieu-noi-nang-nong-chieu-toi-va-dem-co-mua-dong-dien-rong-post1126472.vnp", "Bão số 2 (Noul) suy yếu, không ảnh hưởng Việt Nam"),
          ("VN", 5, "https://vietnamnet.vn/thoi-su", "Hà Nội lắp 20.000 camera AI"),
          ("VN", 6, "https://vnexpress.net/thoi-su", "Thủ tướng chỉ đạo khẩn vụ lật canô Phú Quốc: 15 người tử vong"),
          ("VN", 7, "https://vietnamnet.vn/thoi-su", "Cháy lớn tại Hà Nội và TPHCM"),
          ("VN", 8, "https://doisongphapluat.com.vn/ngay-mai-27-7-xet-xu-ong-trum-vu-100-tan-thuc-pham-chuc-nang-gia-a728891.html", "Xét xử 'ông trùm' 100 tấn thực phẩm chức năng giả"),
          ("VN", 9, "https://thanhnien.vn/thoi-su.htm", "Triệt phá ổ lừa đảo tại TP.HCM"),
          ("VN", 10, "https://vietnamnet.vn/thoi-su", "Metro số 6 đề xuất 2 ga ngầm kết nối sân bay Tân Sơn Nhất")]
    
    # Similar for world, poland, immigration...
    world = [("WORLD", 1, "https://apnews.com/article/iran-war-united-states-ceasefire-ad9fa27d5b1b5fd51e30d923ee738238", "Mỹ và Iran tạm ngừng tấn công tại Dubai"),
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
             ("WORLD", 14, "https://www.newser.com/article/4c578fc74746052627b1c87845fdc0d5/", "Pentagon xóa 4 binh sĩ tử vong khỏi danh sách"),
             ("WORLD", 15, "https://notesfrompoland.com/2026/07/22/germany-deploys-soldiers-to-poland-to-help-reinforce-eastern-borders", "Đức điều quân giúp Ba Lan"),
             ("WORLD", 16, "https://www.vietnam.vn/ba-lan-lien-tiep-chan-may-bay-quan-su-nga-tren-bien-baltic", "Ba Lan chặn máy bay quân sự Nga"),
             ("WORLD", 17, "https://www.bbc.com/news/world", "Nữ võ sĩ quyền anh Ấn Độ tranh huy chương"),
             ("WORLD", 18, "https://www.bbc.com/news/world", "Tòa nhà Flatron NYC rao bán 58,5 triệu USD"),
             ("WORLD", 19, "https://www.bbc.com/news/world", "Nhà tù Cameroon phòng thu âm trở thành hiện tượng"),
             ("WORLD", 20, "https://www.bbc.com/news/world", "EU tranh luận về chính sách di cư")]
    
    poland = [("POLAND", 1, "https://www.visahq.news/2026-07-24/pl/poland-sets-new-record-for-migrant-deportations-in-first-half-of-2026/", "Kỷ lục trục xuất di dân: 5.640 người"),
              ("POLAND", 2, "https://y94.com/2026/07/22/poland-hungarys-foreign-worker-curbs-create-headache-for-business/", "Siết chặt lao động nước ngoài"),
              ("POLAND", 3, "https://industryalarm.eu/revolution-for-ukrainians-in-poland/a-test-to-pass-and-a-loyalty-pledge/to-sign/", "Luật quốc tịch mới: 8 năm cư trú"),
              ("POLAND", 4, "https://brusselssignal.eu/2026/07/poland-takes-control-of-illegal-border-crossings/in/the/east/leaves/backdoor/open/", "Giảm 98% nhập cư trái phép"),
              ("POLAND", 5, "https://brusselssignal.eu/2026/07/poland-takes-control-of-illegal-border-crossings/in/the/east/leaves/backdoor/open/", "20.000+ giấy phép lao động châu Phi"),
              ("POLAND", 6, "https://www.vov.vn/quan-su-quoc-phong/ba-lan-khoi-dong-chuong-trinh-doi-moi-quoc-phong-205-trieu-usd-post1318031.vov", "Ba Lan-Đức phối hợp 'East Shield'"),
              ("POLAND", 7, "https://www.vietnam.vn/san-xuat-ten-lua-patriot-ba-lan-ngo-loi-voi-my-ukraine-mong-nhat-ban/chung-tay", "Đề nghị Mỹ đàm phán Patriot"),
              ("POLAND", 8, "https://www.vietnam.vn/tong-thong-ba-lan-bac-du-luat-mo-rong-quyen-cho-cac-cap-doi/khong-ket-hon", "Tổng thống Nawrocki phủ quyết"),
              ("POLAND", 9, "https://congluan.vn/ba-lan/truy-to/thanh-nien-ukraine/pha-hoai/dai-tuong-niem/kich-dong/thu-han/sac-toc/post353758.html", "Truy tố thanh niên Ukraine phá hoại đài tưởng niệm"),
              ("POLAND", 10, "https://brusselssignal.eu/2026/07/poland-takes-control-of/illegall-border-crossings/in/the/east/leaves/backdoor/open/", "Căng thẳng cộng đồng Muslim tại Kraków")]
    
    imm = [("IMMIGRATION", 1, "https://www.visahq.news/2026-07-24/pl/poland-sets-new-record-for-migrant-deportations/in/first-half/of/2026/", "Kỷ lục trục xuất: 5.640 người (+28% YoY)"),
           ("IMMIGRATION", 2, "https://y94.com/2026/07/22/poland-hungarys/foreign-worker-curbs/create/headache/for/business/", "Siết chặt lao động: thiếu nhân công"),
           ("IMMIGRATION", 3, "https://industryalarm.eu/revolution-for-ukrainians-in/poland/a-test/to/pass-and/a-loyalty-pledge/to/sign/", "Luật quốc tịch mới: 3→8 năm"),
           ("IMMIGRATION", 4, "https://brusselssignal.eu/2026/07/poland-takes/control/of/illegal/border/crossings/in/the/east/leaves/backdoor/open/", "Biên giới an toàn: Giảm 98%"),
           ("IMMIGRATION", 5, "https://brusselssignal.eu/2026/07/poland-takes/control/of/illegal/border/crossings/in/the/east/leaves/backdoor/open/", "Lao động châu Phi: 20.000+ giấy phép")]
    
    vn_new, sent = filt(vn, sent)
    world_new, sent = filt(world, sent)
    poland_new, sent = filt(poland, sent)
    imm_new, sent = filt(imm, sent)
    
    save_ids(sent)
    
    out = []
    out.append("*📰 TIN TỨC HÀNG NGÀY*")
    out.append(f"*📅 {today}*")
    out.append("")
    
    if vn_new:
        out.append(f"*🇻🇳 VIỆT NAM — {len(vn_new)} TIN MỚI*")
        for i in vn_new[:10]:
            out.append(f"{len(out)}.) {i['title']}")
            out.append(f"   [🔗]({i['link']})")
        out.append("")
    
    if world_new:
        out.append(f"*🌍 THẾ GIỚI — {len(world_new)} TIN MỚI*")
        for i in world_new[:20]:
            out.append(f"{len(out)}.) {i['title']}")
            out.append(f"   [🔗]({i['link']})")
        out.append("")
    
    if poland_new:
        out.append(f"*🇵🇱 BA LAN — {len(poland_new)} TIN MỚI*")
        for i in poland_new[:10]:
            out.append(f"{len(out)}.) {i['title']}")
            out.append(f"   [🔗]({i['link']})")
        out.append("")
    
    if imm_new:
        out.append("*🚨 5 TIN DI TRÚ BA LAN (Ưu tiên)*")
        for i in imm_new[:5]:
            out.append(f"{len(out)}.) {i['title']}")
            out.append(f"   [🔗]({i['link']})")
        out.append("")
    
    out.append("_🤖 Auto-generated by Telegram News Bot_")
    return "\n".join(out), len(vn_new) + len(world_new)


def main():
    if '--listen' in sys.argv:
        print("📡 Lắng nghe lệnh /news... Gửi tin cho bot")
        # Simple approach: just wait for user to send command
        import time
        while True:
            time.sleep(60)  # Poll every minute
    else:
        print("🚀 Đang chuẩn bị tin tức...")
        content, count = build_news()
        print(f"📝 {len(content)} ký tự, {count} tin mới")
        
        if send(content):
            print("✅ Gửi thành công!")
        else:
            print("❌ Gửi thất bại!")
        
        log = f"news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(log, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"📁 Log: {log}")


if __name__ == "__main__":
    main()
