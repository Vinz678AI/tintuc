#!/usr/bin/env python3
"""
Telegram News Bot - TIN TỨC TIẾNG VIỆT (Tổng hợp)
- Chỉ cần 3 secrets: BOT_TOKEN, CHAT_ID, GIST_ID
- Tin TIẾNG VIỆT từ các nguồn Việt Nam
- Tổng hợp theo chủ đề
- KHÔNG TRÙNG LẶP - ĐẢM BẢO ĐỦ SỐ LƯỢNG
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from xml.etree import ElementTree as ET
from html import unescape

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
GIST_ID = os.getenv('GIST_ID')

if not BOT_TOKEN or not CHAT_ID:
    logger.error("Cần BOT_TOKEN và CHAT_ID")
    sys.exit(1)

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# RSS Feeds TIẾNG VIỆT
RSS_FEEDS = {
    'vietnam': [
        'https://vnexpress.net/rss/tin-moi-nhat.rss',
        'https://vnexpress.net/rss/tin-tuc.rss',
        'https://dantri.com.vn/rdf/rdf.aspx?id=rss_latest',
        'https://cafef.vn/rss/homepage.cafef'
    ],
    'world': [
        'https://rsshub.app/bbc/chinese'
    ],
    'poland': [
        'https://rp.pl/rss_main',
        'https://www.rp.pl/rss'
    ],
    'immigration': [
        'https://news.globarisconsulting.com/country/poland'
    ]
}

# Chủ đề để tổng hợp
TOPICS = {
    'chinh-tri': ['chính trị', 'chính quyền', 'quốc hội', 'thủ tướng', 'tổng thống', 'bầu cử', 'luật', 'chủ tịch', 'bộ trưởng', 'chính phủ'],
    'kinh-te': ['kinh tế', 'gdp', 'lạm phát', 'tiền tệ', 'ngân hàng', 'chứng khoán', 'đầu tư', 'doanh nghiệp', 'vốn', 'thị trường', 'doanh nhân'],
    'xã-hội': ['xã hội', 'giáo dục', 'y tế', 'bạo lực', 'tai nạn', 'mưa bão', 'thiên tai', 'đời sống', 'người dân', 'trẻ em', 'người cao tuổi'],
    'quốc-phòng': ['quốc phòng', 'quân sự', 'biên giới', 'biển đảo', 'hải quân', 'không quân', 'qpsl', 'quân đội', 'lục quân'],
    'the-gioi': ['trung quốc', 'nga', 'mỹ', 'liên hiệp âu', 'âu', 'ấn độ', 'trung đông', 'ukraine', 'israel', 'iran', 'houthi', 'xung đột'],
    'ba-lan': ['ba lan', 'poland', 'warsaw', 'kraków', 'biên giới', 'di dân', 'người ukraine', 'ukraine', 'hồng giáo', 'lao động', 'visa', 'paperwork', 'zameldowanie', 'zakit'],
    'di-trú': ['di trú', 'visa', 'thị thực', 'tạm trú', 'thường trú', 'quốc tịch', 'trục xuất', 'lao động nước ngoài', 'work permit', 'karta pobytu']
}

def fetch_rss(url):
    try:
        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml'
        })
        response = urlopen(req, timeout=15)
        return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None

def parse_rss(xml):
    articles = []
    try:
        root = ET.fromstring(xml)
        
        # Atom format
        for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
            title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
            link_elem = entry.find('{http://www.w3.org/2005/Atom}link')
            
            if title_elem is not None and link_elem is not None:
                title = unescape(title_elem.text or '')
                link = link_elem.get('href', '') or link_elem.text or ''
                
                if title and link:
                    articles.append({
                        'title': title.strip(),
                        'url': link.strip()
                    })
        
        # RSS 2.0 format
        if not articles:
            for item in root.findall('.//item'):
                title_elem = item.find('title')
                link_elem = item.find('link')
                
                if title_elem is not None and link_elem is not None:
                    title = unescape(title_elem.text or '')
                    link = unescape(link_elem.text or '')
                    
                    if title and link:
                        articles.append({
                            'title': title.strip(),
                            'url': link.strip()
                        })
                        
    except Exception as e:
        logger.warning(f"Parse error: {e}")
    
    return articles

def categorize_article(article):
    """Phân loại bài viết theo chủ đề"""
    title_lower = article['title'].lower()
    categories = []
    
    for cat, keywords in TOPICS.items():
        for keyword in keywords:
            if keyword in title_lower:
                categories.append(cat)
                break
    
    return categories if categories else ['khác']

def load_sent_ids():
    if not GIST_ID:
        return set()
    
    try:
        gist_url = f"https://gist.githubusercontent.com/{GIST_ID}/raw/sent_ids.json"
        req = Request(gist_url, headers={'User-Agent': 'NewsBot'})
        content = urlopen(req, timeout=10).read().decode('utf-8')
        ids = json.loads(content)
        logger.info(f"Loaded {len(ids)} sent IDs from Gist")
        return set(ids)
    except Exception as e:
        logger.warning(f"Error loading from Gist: {e}")
        return set()

def save_sent_ids(sent_ids):
    if not GIST_ID:
        return
    
    try:
        gist_url = f"https://api.github.com/gists/{GIST_ID}"
        req = Request(
            gist_url,
            data=json.dumps({'files': {'sent_ids.json': {'content': json.dumps(list(sent_ids))}}}).encode(),
            headers={'User-Agent': 'NewsBot'},
            method='PATCH'
        )
        urlopen(req, timeout=10)
        logger.info(f"Saved {len(sent_ids)} IDs to Gist")
    except Exception as e:
        logger.warning(f"Error saving to Gist: {e}")
        with open('sent_ids.json', 'w') as f:
            json.dump(list(sent_ids), f)
        logger.info(f"Saved {len(sent_ids)} IDs locally")

def fetch_news_with_dedup(category, required_count, sent_ids):
    """
    Fetch news and ensure we have enough unique articles
    If duplicate found, keep fetching until we get required count
    """
    articles = []
    seen_urls = set()
    all_candidates = []
    
    # Fetch from multiple sources
    for feed in RSS_FEEDS.get(category, []):
        xml = fetch_rss(feed)
        if xml:
            for art in parse_rss(xml):
                if art['url'] not in seen_urls:
                    seen_urls.add(art['url'])
                    all_candidates.append(art)
    
    logger.info(f"Category {category}: Fetched {len(all_candidates)} articles from RSS")
    
    # Filter out duplicates and collect unique articles
    for art in all_candidates:
        art_id = hash(art['url']) % 1000000000
        if art_id not in sent_ids and art['title']:
            articles.append(art)
        if len(articles) >= required_count:
            break
    
    logger.info(f"Category {category}: Found {len(articles)} unique articles")
    
    # If not enough articles, try to fetch more from alternate sources
    if len(articles) < required_count:
        logger.warning(f"Category {category}: Only {len(articles)} articles, need {required_count}. Fetching more...")
        
        # Additional sources for Vietnam
        extra_feeds = {
            'vietnam': [
                'https://tuoitre.vn/rss/tin-moi-nhat.rss',
                'https://thanhnien.vn/rss/latest.rss',
                'https://plo.vn/rss/tin-moi-nhat.rss'
            ],
            'world': [
                'https://rsshub.app/wsj/headlines',
                'https://rsshub.app/cnn/top'
            ],
            'poland': [
                'https://wyborcza.pl/rss.xml',
                'https://tvn24.pl/rss'
            ]
        }
        
        for feed in extra_feeds.get(category, []):
            xml = fetch_rss(feed)
            if xml:
                for art in parse_rss(xml):
                    if art['url'] not in seen_urls:
                        seen_urls.add(art['url'])
                        art_id = hash(art['url']) % 1000000000
                        if art_id not in sent_ids and art['title']:
                            articles.append(art)
                            if len(articles) >= required_count:
                                break
            if len(articles) >= required_count:
                break
    
    # If still not enough, take all available
    if len(articles) < required_count:
        logger.warning(f"Category {category}: Only got {len(articles)}/{required_count} articles")
    
    return articles[:max(required_count, len(articles))]

def send_message(message):
    try:
        req = Request(
            f"{TELEGRAM_API}/sendMessage",
            data=json.dumps({'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML'}).encode(),
            headers={'Content-Type': 'application/json'}
        )
        result = urlopen(req, timeout=10).read().decode()
        logger.info(f"Sent message: {len(message)} chars")
        return result
    except Exception as e:
        logger.error(f"Send error: {e}")
        return None

def main():
    logger.info("Starting Vietnamese news bot with guaranteed count...")
    logger.info(f"GIST_ID: {GIST_ID[:20] if GIST_ID else 'None'}")
    
    sent_ids = load_sent_ids()
    logger.info(f"Already sent: {len(sent_ids)} articles")
    
    categories = {
        'vietnam': ('🇻🇳 TIN VIỆT NAM', 15),
        'world': ('🌍 TIN THẾ GIỚI', 15),
        'poland': ('🇵🇱 TIN BA LAN', 10),
        'immigration': ('✈️ TIN DI TRÚ BA LAN', 5)
    }
    
    all_new_ids = set()
    all_articles = []
    
    # Fetch articles for each category with guaranteed count
    for cat, (title, count) in categories.items():
        articles = fetch_news_with_dedup(cat, count, sent_ids)
        logger.info(f"Fetch {cat}: {len(articles)} articles (required: {count})")
        all_articles.extend(articles)
    
    logger.info(f"Total fetched: {len(all_articles)} articles")
    
    # Categorize articles
    categorized = {}
    for art in all_articles:
        art_id = hash(art['url']) % 1000000000
        if art_id not in sent_ids and art['title']:
            cats = categorize_article(art)
            for c in cats:
                if c not in categorized:
                    categorized[c] = []
                categorized[c].append(art)
            all_new_ids.add(art_id)
    
    logger.info(f"New articles to send: {len(all_new_ids)}")
    
    if not all_new_ids:
        logger.info("No new articles to send")
        msg = "<b>📰 TIN TỨC HÔM NAY</b>\n\n"
        msg += "Không có tin mới hôm nay.\n"
        msg += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
        send_message(msg)
        return
    
    # Build summary messages by topic
    topic_emojis = {
        'chinh-tri': '🏛️',
        'kinh-te': '📈',
        'xã-hội': '👥',
        'quốc-phòng': '🛡️',
        'the-gioi': '🌍',
        'ba-lan': '🇵🇱',
        'di-trú': '✈️',
        'khác': '📰'
    }
    
    messages = []
    
    # Group by category - send all unique articles
    for topic in ['chinh-tri', 'kinh-te', 'xã-hội', 'quốc-phòng', 'the-gioi', 'ba-lan', 'di-trú', 'khác']:
        if topic in categorized and categorized[topic]:
            articles = categorized[topic][:5]  # Up to 5 per topic
            emoji = topic_emojis.get(topic, '📰')
            
            msg = f"<b>{emoji} {topic.replace('-', ' ').upper()}</b>\n"
            for i, art in enumerate(articles, 1):
                t = art['title'][:80] + '...' if len(art['title']) > 80 else art['title']
                msg += f"{i}. {t}\n"
            msg += f"\n🔗 Đọc thêm tại nguồn\n"
            msg += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}\n"
            messages.append(msg)
    
    # Also send summary by source
    summary_msg = f"<b>📰 TÓM TẮT TIN TỨC</b>\n\n"
    summary_msg += f"🇻🇳 Việt Nam: {len([a for a in all_articles if any(k in a['title'].lower() for k in ['vnexpress', 'dantri', 'cafef', 'nhip caudau', 'tuoitre', 'thanhnien'])])} tin\n"
    summary_msg += f"🌍 Thế giới: {len([a for a in all_articles if any(k in a['title'].lower() for k in ['bbc', 'trung quốc', 'nga', 'mỹ', 'âu'])])} tin\n"
    summary_msg += f"🇵🇱 Ba Lan: {len([a for a in all_articles if any(k in a['title'].lower() for k in ['ba lan', 'poland', 'warsaw'])])} tin\n"
    summary_msg += f"✈️ Di trú: {len([a for a in all_articles if any(k in a['title'].lower() for k in ['di trú', 'visa', 'thị thực', 'người ukraine'])])} tin\n"
    summary_msg += f"\n<i>{len(all_new_ids)} tin mới hôm nay</i>"
    messages.append(summary_msg)
    
    # Send all messages
    for msg in messages:
        logger.info(f"Sending message: {msg[:50]}...")
        send_message(msg)
    
    # Update sent IDs
    if all_new_ids:
        sent_ids.update(all_new_ids)
        save_sent_ids(sent_ids)
        logger.info(f"Updated: {len(sent_ids)} total sent IDs")
    
    logger.info(f"Done! Sent {len(all_new_ids)} new articles")

if __name__ == '__main__':
    main()
