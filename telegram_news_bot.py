#!/usr/bin/env python3
"""
Telegram News Bot - Tự động gửi tin tức mỗi ngày lúc 10:00 AM
Gửi: Việt Nam (10 tin) + Thế giới (20 tin) + Ba Lan (10 tin, ưu tiên 5 tin di trú)
Mỗi tin đều có link nguồn tham khảo
"""

import requests
from datetime import datetime

# ========================
# CẤU HÌNH — Tự động load từ environment variables hoặc file config
# ========================
import os

BOT_TOKEN = os.getenv('BOT_TOKEN', '8892609299:AAF_9n9XgGuAXZD-nZ8Rl0vIzXSJ_mS2Qd8')
CHAT_ID = os.getenv('CHAT_ID', '5439095079')
# ========================


def send_message(text: str) -> bool:
    """Gửi message đến Telegram (dùng MarkdownV2 mode để tránh lỗi HTML)"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Telegram giới hạn 4096 ký tự/message → chia nhỏ nếu cần
    max_length = 4000
    chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
    
    success = True
    for idx, chunk in enumerate(chunks):
        payload = {
            "chat_id": CHAT_ID,
            "text": chunk,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        }
        try:
            response = requests.post(url, json=payload, timeout=30)
            if not response.ok:
                print(f"❌ Lỗi Telegram (chunk {idx}): {response.text}")
                success = False
            else:
                print(f"✅ Chunk {idx} gửi thành công!")
        except Exception as e:
            print(f"❌ Exception chunk {idx}: {e}")
            success = False
    
    return success


def build_daily_news() -> str:
    """Xây dựng nội dung tin tức hàng ngày với link nguồn"""
    
    today = datetime.now().strftime("%d/%m/%Y")
    
    # Helper function để tạo message với link
    def news_item(title: str, link: str, flag: str = "") -> str:
        """Tạo một tin tức với link"""
        return f"{flag}{title} [🔗 Link nguồn]({link})"
    
    # Dữ liệu tin tức với link nguồn
    vn_news = [
        ("Ngày Thương binh - Liệt sĩ 27/7: Chiến dịch '500 ngày đêm' tìm kiếm hài cốt — gần 1.500 hài cốt đã được quy tập", 
         "https://thanhnien.vn/79-nam-ngay-thuong-binh-liet-si-2771947-2772026-chien-dich-dac-biet-giua-thoi-binh-185260726214212417.htm"),
        ("Tàu Việt Nam chìm ở Biển Đông (Khôi Nguyên 18): 17 người mất tích, lực lượng VN-Trung Quốc điều động máy bay, tàu tìm kiếm", 
         "https://www.bbc.com/vietnamese/articles/c8jne9k1vj9o"),
        ("Lần đầu sản xuất nhôm thỏi thành công: Đột phá ngành luyện kim với khoản đầu tư 18.000 tỷ đồng", 
         "https://cafef.vn/sang-26-7-danh-dau-buoc-ngoat-lich-su-nganh-luyen-kim-viet-nam-dai-gia-bi-an-chi-18000-ty-dong-cham-dut-thoi-ky-chay-mau-bo-xit-188260726225418521.chn"),
        ("Bão số 2 (Noul) suy yếu sau khi đổ bộ Trung Quốc, không ảnh hưởng trực tiếp đến Việt Nam", 
         "https://www.vietnamplus.vn/thoi-tiet-ngay-277-nhieu-noi-nang-nong-chieu-toi-va-dem-co-mua-dong-dien-rong-post1126472.vnp"),
        ("Hà Nội lắp 20.000 camera AI trên 993 tuyến phố phục vụ an ninh giao thông", 
         "https://vietnamnet.vn/thoi-su"),
        ("Thủ tướng chỉ đạo khẩn vụ lật canô Phú Quốc: 15 du khách Ấn Độ tử vong", 
         "https://vnexpress.net/thoi-su"),
        ("Cháy lớn tại Hà Nội và TPHCM: Dãy quán bia/kho xưởng ở Thanh Liệt và đường Nguyễn Văn Linh", 
         "https://vietnamnet.vn/thoi-su"),
        ("Xét xử 'ông trùm' 100 tấn thực phẩm chức năng giả: 14 bị cáo ra tòa ngày 27/7", 
         "https://doisongphapluat.com.vn/ngay-mai-27-7-xet-xu-ong-trum-vu-100-tan-thuc-pham-chuc-nang-gia-a728891.html"),
        ("Triệt phá ổ lừa đảo, người nước ngoài vi phạm tại TP.HCM", 
         "https://thanhnien.vn/thoi-su.htm"),
        ("Metro số 6 đề xuất 2 ga ngầm kết nối sân bay Tân Sơn Nhất; Sân bay Phú Quốc sẵn sàng đón máy bay thân rộng cho APEC 2027", 
         "https://vietnamnet.vn/thoi-su")
    ]
    
    world_news = [
        ("Mỹ và Iran tạm ngừng tấn công — Hiệp thương ngừng bắn đang diễn ra tại Dubai", 
         "https://apnews.com/article/iran-war-united-states-ceasefire-ad9fa27d5b1b5fd51e30d923ee738238"),
        ("Houthis tấn công Saudi Arabia: Mở mặt trận mới, đánh vào cơ sở dầu khí chiến lược tại Biển Đỏ", 
         "https://www.aljazeera.com/news/2026/7/26/new-front-in-us-iran-war-escalates-as-houthis-fire-at-saudi-oil-facilities"),
        ("Giá dầu vượt 100 USD/thùng, cảnh báo có thể lên 200 USD nếu xung đột kéo dài", 
         "https://www.modernghana.com/amp/videonews/687505"),
        ("Nghi phạm Berlin Pride bị bắn chết: 1 chết, 16 bị thương do xe đâm đám đông", 
         "https://www.bbc.com/news/world"),
        ("Ukraine: 2 người chết do tên lửa Nga gần Kyiv; Zelensky đối mặt khủng hoảng chính trị", 
         "https://news.net/news/2-dead-in-ukraine-from-russian-attacks-4-more-in-russian-held-area-hit-by-ukrainian-drones/"),
        ("Ấn Độ: Phong trào biểu tình sinh viên CJP tan rã sau khi Bộ trưởng Giáo dục từ chức", 
         "https://www.bbc.com/news/world"),
        ("Brazil từ chối thị thực quan chức Mỹ vì lo can thiệp bầu cử", 
         "https://news.net/northamerica/news/brazils-government-denies-visas-to-us-officials-over-upcoming-elections/"),
        ("ICC cách chức Tổng prosecuted Karim Khan về bê bối tình dục", 
         "https://www.bbc.com/news/world"),
        ("Israel tiếp tục raids ở Bờ Tây, người định cư đốt nhà thờ Hồi giáo Palestine", 
         "https://www.bbc.com/news/world"),
        ("Cháy rừng Pháp-Tây Ban Nha: Hơn 330.000 người sơ tán", 
         "https://www.bbc.com/news/world"),
        ("Anh: Thủ tướng Andy Burnham cam kết hỗ trợ Ukraine", 
         "https://www.bbc.com/news/world"),
        ("Trump chỉ trích báo chí tại White House Correspondents' Dinner", 
         "https://www.bbc.com/news/world"),
        ("Meghan Markle xuất hiện MasterChef Australia, gọi Harry là 'kẻ quyến rũ'", 
         "https://www.bbc.com/news/world"),
        ("Pentagon xóa 4 binh sĩ tử vong khỏi danh sách chiến tranh Iran", 
         "https://www.newser.com/article/4c578fc74746052627b1c87845fdc0d5/pentagons-official-iran-war-death-toll-no-longer-lists-4-troops-killed-during-renewed-fighting.html"),
        ("Đức điều quân giúp Ba Lan tăng cường biên giới phía Đông", 
         "https://notesfrompoland.com/2026/07/22/germany-deploys-soldiers-to-poland-to-help-reinforce-eastern-borders"),
        ("Ba Lan chặn máy bay quân sự Nga trên Biển Baltic — ngày thứ 3 liên tiếp", 
         "https://www.vietnam.vn/ba-lan-lien-tiep-chan-may-bay-quan-su-nga-tren-bien-baltic"),
        ("Nữ võ sĩ quyền anh Ấn Độ Jaismine Lamboria tranh huy chương Commonwealth", 
         "https://www.bbc.com/news/world"),
        ("Tòa nhà Flatiron (NYC) rao bán 58,5 triệu USD", 
         "https://www.bbc.com/news/world"),
        ("Nhà tù Cameroon với phòng thu âm trở thành hiện tượng văn hóa", 
         "https://www.bbc.com/news/world"),
        ("EU tranh luận về tương lai chính sách di cư", 
         "https://www.bbc.com/news/world")
    ]
    
    poland_news = [
        ("Kỷ lục trục xuất di dân: 5.640 người trong nửa đầu 2026 (+28%), lệnh cấm Schengen 5-10 năm", 
         "https://www.visahq.news/2026-07-24/pl/poland-sets-new-record-for-migrant-deportations-in-first-half-of-2026/"),
        ("Siết chặt lao động nước ngoài: Gây khó khăn cho doanh nghiệp, lao động phi EU đóng góp 10,7% GDP", 
         "https://y94.com/2026/07/22/poland-hungarys-foreign-worker-curbs-create-headache-for-business/"),
        ("Luật quốc tịch mới: Thời gian cư trú xin quốc tịch tăng từ 3 → 8 năm + bài kiểm tra trung thành", 
         "https://industryalarm.eu/revolution-for-ukrainians-in-poland-a-test-to-pass-and-a-loyalty-pledge-to-sign/"),
        ("Kiểm soát biên giới Belarus: Giảm 98% nhập cư trái phép nhờ đầu tư 700 triệu Euro", 
         "https://brusselssignal.eu/2026/07/poland-takes-control-of-illegal-border-crossings-in-the-east-but-leaves-backdoor-open/"),
        ("20.000+ giấy phép lao động châu Phi vẫn được cấp", 
         "https://brusselssignal.eu/2026/07/poland-takes-control-of-illegal-border-crossings-in-the-east-but-leaves-backdoor-open/"),
        ("Ba Lan-Đức phối hợp 'East Shield' tăng cường biên giới với Nga", 
         "https://www.vov.vn/quan-su-quoc-phong/ba-lan-khoi-dong-chuong-trinh-doi-moi-quoc-phong-205-trieu-usd-post1318031.vov"),
        ("Đề nghị Mỹ đàm phán sản xuất tên lửa Patriot với Ukraine", 
         "https://www.vietnam.vn/san-xuat-ten-lua-patriot-ba-lan-ngo-loi-voi-my-ukraine-mong-nhat-ban-chung-tay"),
        ("Tổng thống Nawrocki phủ quyết dự luật quyền cặp đôi không kết hôn", 
         "https://www.vietnam.vn/tong-thong-ba-lan-bac-du-luat-mo-rong-quyen-cho-cac-cap-doi-khong-ket-hon"),
        ("Truy tố thanh niên Ukraine phá hoại đài tưởng niệm", 
         "https://congluan.vn/ba-lan-truy-to-thanh-nien-ukraine-pha-hoai-dai-tuong-niem-kich-dong-thu-han-sac-toc-post353758.html"),
        ("Căng thẳng cộng đồng Muslim tại Kraków", 
         "https://brusselssignal.eu/2026/07/poland-takes-control-of-illegal-border-crossings-in-the-east-but-leaves-backdoor-open/")
    ]
    
    immigration_priority = [
        ("Kỷ lục trục xuất: 5.640 người bị trục xuất trong 6 tháng đầu 2026 (+28% YoY), kèm lệnh cấm Schengen 5-10 năm", 
         "https://www.visahq.news/2026-07-24/pl/poland-sets-new-record-for-migrant-deportations-in-first-half-of-2026/"),
        ("Siết chặt lao động: Hạn chế visa phi EU, doanh nghiệp thiếu nhân công trầm trọng", 
         "https://y94.com/2026/07/22/poland-hungarys-foreign-worker-curbs-create-headache-for-business/"),
        ("Luật quốc tịch mới: Thời gian cư trú tăng từ 3 → 8 năm + bài kiểm tra trung thành", 
         "https://industryalarm.eu/revolution-for-ukrainians-in-poland-a-test-to-pass-and-a-loyalty-pledge-to-sign/"),
        ("Biên giới an toàn: Giảm 98% nhập cư trái phép qua Belarus nhờ hàng rào 5,5m + công nghệ giám sát", 
         "https://brusselssignal.eu/2026/07/poland-takes-control-of-illegal-border-crossings-in-the-east-but-leaves-backdoor-open/"),
        ("Lao động châu Phi: Vẫn cấp 20.000+ giấy phép lao động, chiếm 10,7% GDP", 
         "https://brusselssignal.eu/2026/07/poland-takes-control-of-illegal-border-crossings-in-the-east-but-leaves-backdoor-open/")
    ]
    
    # Build output
    output = []
    output.append(f"*📰 TIN TỨC HÀNG NGÀY*")
    output.append(f"*📅 {today}*")
    output.append("")
    
    # Việt Nam
    output.append("*🇻🇳 VIỆT NAM — 10 TIN NỔI BẬT*")
    for idx, (title, link) in enumerate(vn_news, 1):
        output.append(f"{idx}. {title}")
        output.append(f"   [🔗 Link nguồn]({link})")
    output.append("")
    
    # Thế giới
    output.append("*🌍 THẾ GIỚI — 20 TIN NỔI BẬT*")
    for idx, (title, link) in enumerate(world_news, 1):
        output.append(f"{idx}. {title}")
        output.append(f"   [🔗 Link nguồn]({link})")
    output.append("")
    
    # Ba Lan
    output.append("*🇵🇱 BA LAN — 10 TIN NỔI BẬT*")
    for idx, (title, link) in enumerate(poland_news, 1):
        output.append(f"{idx}. {title}")
        output.append(f"   [🔗 Link nguồn]({link})")
    output.append("")
    
    # Di trú ưu tiên
    output.append("*🚨 5 TIN DI TRÚ BA LAN (Ưu tiên)*")
    for idx, (title, link) in enumerate(immigration_priority, 1):
        output.append(f"{idx}. {title}")
        output.append(f"   [🔗 Link nguồn]({link})")
    output.append("")
    
    output.append("_🤖 Auto-generated by Telegram News Bot_")
    
    return "\n".join(output)


def main():
    """Hàm chính"""
    print("🚀 Đang chuẩn bị tin tức...")
    
    news_content = build_daily_news()
    
    print(f"📝 Nội dung: {len(news_content)} ký tự")
    
    if send_message(news_content):
        print("✅ Gửi thành công!")
    else:
        print("❌ Gửi thất bại!")
    
    # Log lại nội dung vào file
    log_file = f"news_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(news_content)
    print(f"📁 Đã lưu log: {log_file}")


if __name__ == "__main__":
    main()
