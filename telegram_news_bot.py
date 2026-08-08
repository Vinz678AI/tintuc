#!/usr/bin/env python3
"""
Telegram News Bot - TIN TỨC TIẾNG VIỆT (Tổng hợp)
- Chỉ cần 3 secrets: BOT_TOKEN, CHAT_ID, GIST_ID
- Tin tiếng Việt từ các nguồn Việt Nam
- Tổng hợp theo chủ đề
- Không trùng lặp hoàn toàn
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
        'https://e.vnexpress.net/rss/news.rss',
        'https://rss.vietnamnet.vn/rss/vn.rss',
        'https://dantri.com.vn/rdf/rdf.aspx?id=rss_latest',
        'https://cafef.vn/rss/tintuc.rss'
    ],
    'world': [
        'https://rsshub.app/bbc/chinese'
    ],
    'poland': [
        'https://rp.pl/rss_main'
    ],
    'immigration': [
        'https://news.globarisconsulting.com/country/poland'
    ]
}

# Chủ đề để tổng hợp
TOPICS = {
    'chinh-tri': ['chính trị', 'chính quyền', 'quốc hội', 'thủ tướng', 'tổng thống', 'bầu cử', 'luật'],
    'kinh-te': ['kinh tế', 'gdp', 'lạm phát', 'tiền tệ', 'ngân hàng', 'chứng khoán', 'đầu tư', 'doanh nghiệp'],
    'xã-hội': ['xã hội', 'giáo dục', 'y tế', 'bạo lực', 'tai nạn', 'mưa bão', 'thiên tai'],
    'quốc-phòng': ['quốc phòng', 'quân sự', 'biên giới', 'biển đảo', 'hải quân', 'không quân'],
    'the-gioi': ['trung quốc', 'nga', 'mỹ', 'liên hiệp âu', 'âu', 'ấn độ', 'trung đông', 'ukraine', 'israel', 'iran', 'houthi', 'xung đột'],
    'ba-lan': ['ba lan', 'poland', 'warsaw', 'kraków', 'biên giới', 'di dân', 'người ukraine', 'ukraine', 'hồng giáo', 'lao động'],
    'di-trú': ['di trú', 'visa', 'thị thực', 'tạm trú', 'thường trú', 'quốc tịch', 'trục xuất', 'lao động nước ngoài', 'paperwork', 'praca', 'zakit', 'zameldowanie']
}

def fetch_rss(url):
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        return urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None

def parse_rss(xml):
    articles = []
    try:
        root = ET.fromstring(xml)
        
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

def fetch_news(category, max_items):
    articles = []
    seen = set()
    
    for feed in RSS_FEEDS.get(category, []):
        if len(articles) >= max_items:
            break
        xml = fetch_rss(feed)
        if xml:
            for art in parse_rss(xml):
                if art['url'] not in seen:
                    seen.add(art['url'])
                    articles.append(art)
    
    return articles[:max_items]

def send_message(message):
    try:
        req = Request(
            f"{TELEGRAM_API}/sendMessage",
            data=json.dumps({'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML'}).encode(),
            headers={'Content-Type': 'application/json'}
        )
        result = urlopen(req, timeout=10).read().decode()
        logger.info(f"Sent: {len(message)} chars")
        return result
    except Exception as e:
        logger.error(f"Send error: {e}")
        return None

def main():
    logger.info("Starting news bot...")
    logger.info(f"GIST_ID: {GIST_ID[:20] if GIST_ID else 'None'}")
    
    sent_ids = load_sent_ids()
    logger.info(f"Already sent: {len(sent_ids)} articles")
    
    categories = {
        'vietnam': ('🇻🇳 TIN VIỆT NAM', 10),
        'world': ('🌍 TIN THẾ GIỚI', 15),
        'poland': ('🇵🇱 TIN BA LAN', 10),
        'immigration': ('✈️ TIN DI TRÚ BA LAN', 5)
    }
    
    all_new_ids = set()
    all_articles = []
    
    # Fetch all articles
    for cat, (title, count) in categories.items():
        articles = fetch_news(cat, count)
        logger.info(f"Fetch {cat}: {len(articles)} articles")
        all_articles.extend(articles)
    
    logger.info(f"Total fetched: {len(all_articles)} articles")
    
    # Categorize and filter
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
    
    logger.info(f"New articles: {len(all_new_ids)}")
    
    if not all_new_ids:
        logger.info("No new articles to send")
        # Send notification that no new news
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
    
    # Group by category
    for topic in ['chinh-tri', 'kinh-te', 'xã-hội', 'quốc-phòng', 'the-gioi', 'ba-lan', 'di-trú', 'khác']:
        if topic in categorized and categorized[topic]:
            articles = categorized[topic][:3]
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
    summary_msg += f"🇻🇳 Việt Nam: {len([a for a in all_articles if any(k in a['title'].lower() for k in ['vnexpress', 'vietnamnet', 'dantri', 'cafef'])])} tin\n"
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
