#!/usr/bin/env python3
"""
Telegram News Bot - TIN TỨC QUỐC TẾ + DỊCH TIẾNG VIỆT
- Chỉ cần 3 secrets: BOT_TOKEN, CHAT_ID, GIST_ID
- Nguồn: BBC, VOA, RFI, DW (tiếng Anh/Pháp)
- TỰ ĐỘNG DỊCH SANG TIẾNG VIỆT
- Không trùng lặp
"""

import os
import sys
import json
import logging
import re
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

# RSS FEEDS QUỐC TẾ UY TÍN
RSS_FEEDS = {
    'vietnam': [
        'https://vnexpress.net/rss/tin-moi-nhat.rss',
        'https://vnexpress.net/rss/tin-tuc.rss',
        'https://cafef.vn/rss/homepage.cafef',
        'https://tuoitre.vn/rss/tin-moi-nhat.rss'
    ],
    'world': [
        'https://feeds.bbci.co.uk/news/world/rss.xml',
        'https://www.voanews.com/api/collections/stories/1129/rss/10',
        'https://feeds.bbci.co.uk/news/world/europe/rss.xml'
    ],
    'poland': [
        'https://feeds.bbci.co.uk/news/world/europe/rss.xml',
        'https://www.voanews.com/api/collections/stories/1129/rss/10'
    ]
}

# TỪ ĐIỂN DỊCH đơn giản
TRANSLATION_DICT = {
    # Chính trị
    'President': 'Tổng thống',
    'Prime Minister': 'Thủ tướng',
    'Parliament': 'Nghị viện',
    'Government': 'Chính phủ',
    'Election': 'Bầu cử',
    'Vote': 'Bỏ phiếu',
    'Bill': 'Dự luật',
    'Law': 'Luật',
    'Policy': 'Chính sách',
    
    # Kinh tế
    'Economy': 'Kinh tế',
    'GDP': 'GDP',
    'Inflation': 'Lạm phát',
    'Market': 'Thị trường',
    'Stock': 'Cổ phiếu',
    'Bank': 'Ngân hàng',
    'Investment': 'Đầu tư',
    'Trade': 'Thương mại',
    'Currency': 'Tiền tệ',
    
    # Xã hội
    'People': 'Người dân',
    'Child': 'Trẻ em',
    'Student': 'Học sinh',
    'School': 'Trường học',
    'Hospital': 'Bệnh viện',
    'Health': 'Sức khỏe',
    'Crime': 'Tội phạm',
    'Murder': 'Giết người',
    'Death': 'Tử vong',
    'Killed': 'Bị giết',
    'Dead': 'Chết',
    
    # Quốc gia
    'China': 'Trung Quốc',
    'America': 'Mỹ',
    'US': 'Mỹ',
    'USA': 'Mỹ',
    'Russia': 'Nga',
    'Ukraine': 'Ukraine',
    'Poland': 'Ba Lan',
    'Germany': 'Đức',
    'France': 'Pháp',
    'UK': 'Anh',
    'Britain': 'Anh',
    'Japan': 'Nhật Bản',
    'Korea': 'Hàn Quốc',
    'Vietnam': 'Việt Nam',
    'Vietnamese': 'Việt Nam',
    'Europe': 'Châu Âu',
    'Asia': 'Châu Á',
    'Africa': 'Châu Phi',
    
    # Sự kiện
    'War': 'Chiến tranh',
    'Conflict': 'Xung đột',
    'Attack': 'Tấn công',
    'Bombing': 'Trúng bom',
    'Crash': 'Tai nạn',
    'Storm': 'Bão',
    'Flood': 'Lũ lụt',
    'Earthquake': 'Động đất',
    
    # Khác
    'says': 'nói',
    'said': 'nói',
    'announced': 'công bố',
    'reported': 'báo cáo',
    'according': 'theo',
    'new': 'mới',
    'today': 'hôm nay',
    'latest': 'mới nhất',
    'top': 'đặc biệt',
    'breaking': 'nhanh',
    'news': 'tin tức'
}

def translate_text(text):
    """Dịch văn bản tiếng Anh sang tiếng Việt"""
    result = text
    
    # Dịch từng từ/cụm từ
    for en, vi in sorted(TRANSLATION_DICT.items(), key=lambda x: -len(x[0])):
        result = re.sub(re.escape(en), vi, result, flags=re.IGNORECASE)
    
    # Cleanup
    result = result.replace('  ', ' ')
    result = result.strip()
    
    return result

def fetch_rss(url):
    try:
        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml'
        })
        response = urlopen(req, timeout=20)
        return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        logger.warning(f"Failed: {url} - {e}")
        return None

def parse_rss(xml):
    articles = []
    if not xml:
        return articles
    try:
        root = ET.fromstring(xml)
        for item in root.findall('.//item'):
            title = item.find('title')
            link = item.find('link')
            if title is not None and link is not None and title.text and link.text:
                title_text = unescape(title.text.strip())
                link_text = unescape(link.text.strip())
                articles.append({
                    'title': title_text,
                    'url': link_text,
                    'original_title': title_text
                })
    except Exception as e:
        logger.warning(f"Parse error: {e}")
    return articles

def load_sent_ids():
    if not GIST_ID:
        return set()
    try:
        gist_url = f"https://gist.githubusercontent.com/{GIST_ID}/raw/sent_ids.json"
        req = Request(gist_url, headers={'User-Agent': 'NewsBot'})
        content = urlopen(req, timeout=15).read().decode('utf-8')
        ids = json.loads(content)
        logger.info(f"Loaded {len(ids)} IDs from Gist")
        return set(ids)
    except:
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
        urlopen(req, timeout=15)
        logger.info(f"Saved {len(sent_ids)} IDs to Gist")
    except:
        with open('sent_ids.json', 'w') as f:
            json.dump(list(sent_ids), f)

def send_message(message):
    try:
        req = Request(
            f"{TELEGRAM_API}/sendMessage",
            data=json.dumps({'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML'}).encode(),
            headers={'Content-Type': 'application/json'}
        )
        result = urlopen(req, timeout=15).read().decode()
        logger.info(f"Sent message ({len(message)} chars)")
        return result
    except Exception as e:
        logger.error(f"Send error: {e}")
        return None

def main():
    logger.info("="*50)
    logger.info("Starting International News Bot (Translated to Vietnamese)...")
    logger.info("="*50)
    
    sent_ids = load_sent_ids()
    logger.info(f"Already sent: {len(sent_ids)} articles")
    
    all_articles = []
    seen_urls = set()
    
    # Fetch all sources
    for category, feeds in RSS_FEEDS.items():
        logger.info(f"\nFetching {category}...")
        for feed in feeds:
            xml = fetch_rss(feed)
            if xml:
                articles = parse_rss(xml)
                logger.info(f"  {feed}: {len(articles)} articles")
                for art in articles:
                    if art['url'] not in seen_urls:
                        seen_urls.add(art['url'])
                        all_articles.append(art)
    
    logger.info(f"\nTotal fetched: {len(all_articles)} articles")
    
    # Filter duplicates and translate
    unique_articles = []
    for art in all_articles:
        art_id = hash(art['url']) % 1000000000
        if art_id not in sent_ids and art['title']:
            # Dịch tiêu đề
            art['translated_title'] = translate_text(art['title'])
            unique_articles.append(art)
    
    logger.info(f"Unique articles (translated): {len(unique_articles)}")
    
    if not unique_articles:
        msg = "<b>📰 TIN TỨC QUỐC TẾ HÔM NAY</b>\n\n"
        msg += "✅ Đã kiểm tra nhưng KHÔNG CÓ TIN MỚI hôm nay.\n"
        msg += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
        send_message(msg)
        return
    
    # Group articles by category
    vn_articles = [a for a in unique_articles if any(d in a['url'] for d in ['vnexpress', 'cafef', 'tuoitre'])]
    bbc_articles = [a for a in unique_articles if 'bbc' in a['url']]
    voa_articles = [a for a in unique_articles if 'voa' in a['url']]
    
    # Poland articles (from BBC Europe)
    poland_articles = [a for a in bbc_articles if any(k in a['original_title'].lower() for k in ['poland', 'warsaw', 'krakow', 'ukraine', 'europe'])]
    world_articles = [a for a in bbc_articles if a not in poland_articles]
    
    # Remove duplicates between categories
    world_articles = [a for a in world_articles if a not in poland_articles]
    
    logger.info(f"Vietnam: {len(vn_articles)}, World (BBC): {len(world_articles)}, Poland: {len(poland_articles)}")
    
    new_ids = set()
    messages = []
    
    # Summary
    summary = f"<b>📰 TIN TỨC QUỐC TẾ HÔM NAY</b>\n\n"
    summary += f"🇻🇳 Việt Nam: {len(vn_articles)} tin\n"
    summary += f"🌍 Thế giới: {len(world_articles) + len(voa_articles)} tin\n"
    summary += f"🇵🇱 Ba Lan: {len(poland_articles)} tin\n"
    summary += f"\n<i>Tổng: {len(unique_articles)} tin mới (đã dịch sang tiếng Việt)</i>\n"
    summary += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
    messages.append(summary)
    
    # Vietnam news
    if vn_articles:
        msg = "<b>🇻🇳 TIN VIỆT NAM</b>\n\n"
        for i, art in enumerate(vn_articles[:10], 1):
            msg += f"{i}. {art['translated_title']}\n"
            msg += f"🔗 {art['url']}\n\n"
            new_ids.add(hash(art['url']) % 1000000000)
        msg += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
        messages.append(msg)
    
    # World news (BBC)
    if world_articles:
        msg = "<b>🌍 TIN THẾ GIỚI (BBC)</b>\n\n"
        for i, art in enumerate(world_articles[:10], 1):
            msg += f"{i}. {art['translated_title']}\n"
            msg += f"🔗 {art['url']}\n\n"
            new_ids.add(hash(art['url']) % 1000000000)
        msg += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
        messages.append(msg)
    
    # World news (VOA)
    if voa_articles:
        msg = "<b>🌍 TIN THẾ GIỚI (VOA)</b>\n\n"
        for i, art in enumerate(voa_articles[:5], 1):
            msg += f"{i}. {art['translated_title']}\n"
            msg += f"🔗 {art['url']}\n\n"
            new_ids.add(hash(art['url']) % 1000000000)
        msg += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
        messages.append(msg)
    
    # Poland news
    if poland_articles:
        msg = "<b>🇵🇱 TIN BA LAN (BBC)</b>\n\n"
        for i, art in enumerate(poland_articles[:8], 1):
            msg += f"{i}. {art['translated_title']}\n"
            msg += f"🔗 {art['url']}\n\n"
            new_ids.add(hash(art['url']) % 1000000000)
        msg += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
        messages.append(msg)
    
    # Send all messages
    for msg in messages:
        send_message(msg)
    
    # Update Gist
    if new_ids:
        sent_ids.update(new_ids)
        save_sent_ids(sent_ids)
        logger.info(f"Updated: {len(sent_ids)} total IDs")
    
    logger.info(f"Done! Sent {len(unique_articles)} new articles")

if __name__ == '__main__':
    main()
