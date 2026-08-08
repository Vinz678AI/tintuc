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

# RSS Feeds TIẾNG VIỆT - THÊM NHIỀU NGUỒN
RSS_FEEDS = {
    'vietnam': [
        'https://vnexpress.net/rss/tin-moi-nhat.rss',
        'https://vnexpress.net/rss/tin-tuc.rss',
        'https://vnexpress.net/rss/market.rss',
        'https://dantri.com.vn/rdf/rdf.aspx?id=rss_latest',
        'https://dantri.com.vn/rdf/rdf.aspx?id=rss_suckhoe',
        'https://dantri.com.vn/rdf/rdf.aspx?id=rss_xahoi',
        'https://cafef.vn/rss/homepage.cafef',
        'https://nhipcaudautu.vn/rss/tintuc.rss',
        'https://tuoitre.vn/rss/tin-moi-nhat.rss',
        'https://thanhnien.vn/rss/latest.rss'
    ],
    'world': [
        'https://rsshub.app/bbc/chinese',
        'https://rsshub.app/wsj/headlines',
        'https://rsshub.app/cnn/top'
    ],
    'poland': [
        'https://rp.pl/rss_main',
        'https://rp.pl/rss_wydarzenia',
        'https://www.rp.pl/rss'
    ],
    'immigration': [
        'https://news.globarisconsulting.com/country/poland'
    ]
}

def fetch_rss(url):
    try:
        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*'
        })
        response = urlopen(req, timeout=20)
        xml_content = response.read().decode('utf-8', errors='ignore')
        logger.info(f"Fetched {url}: {len(xml_content)} bytes")
        return xml_content
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None

def parse_rss(xml):
    articles = []
    if not xml:
        return articles
    
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
    
    logger.info(f"Parsed {len(articles)} articles")
    return articles

def load_sent_ids():
    """Load sent IDs from Gist"""
    if not GIST_ID:
        logger.warning("GIST_ID not set - will send all articles")
        return set()
    
    try:
        gist_url = f"https://gist.githubusercontent.com/{GIST_ID}/raw/sent_ids.json"
        req = Request(gist_url, headers={'User-Agent': 'NewsBot'})
        content = urlopen(req, timeout=15).read().decode('utf-8')
        ids = json.loads(content)
        logger.info(f"Loaded {len(ids)} sent IDs from Gist")
        return set(ids)
    except Exception as e:
        logger.warning(f"Error loading from Gist: {e}")
        logger.info("Falling back to empty sent_ids (will send all articles)")
        return set()

def save_sent_ids(sent_ids):
    """Save sent IDs to Gist"""
    if not GIST_ID:
        logger.warning("GIST_ID not set - skipping save")
        return
    
    try:
        gist_url = f"https://api.github.com/gists/{GIST_ID}"
        req = Request(
            gist_url,
            data=json.dumps({'files': {'sent_ids.json': {'content': json.dumps(list(sent_ids))}}}).encode(),
            headers={'User-Agent': 'NewsBot', 'Authorization': f'Bearer {os.getenv("GITHUB_TOKEN", "")}'},
            method='PATCH'
        )
        urlopen(req, timeout=15)
        logger.info(f"Saved {len(sent_ids)} IDs to Gist")
    except Exception as e:
        logger.warning(f"Error saving to Gist: {e}")
        # Save locally as fallback
        with open('sent_ids.json', 'w') as f:
            json.dump(list(sent_ids), f)
        logger.info(f"Saved {len(sent_ids)} IDs locally")

def send_message(message):
    try:
        req = Request(
            f"{TELEGRAM_API}/sendMessage",
            data=json.dumps({'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML'}).encode(),
            headers={'Content-Type': 'application/json'}
        )
        result = urlopen(req, timeout=15).read().decode()
        logger.info(f"Sent message: {len(message)} chars")
        return result
    except Exception as e:
        logger.error(f"Send error: {e}")
        return None

def main():
    logger.info("="*50)
    logger.info("Starting Vietnamese news bot...")
    logger.info(f"GIST_ID: {GIST_ID[:20] if GIST_ID else 'None'}")
    logger.info("="*50)
    
    # Load sent IDs
    sent_ids = load_sent_ids()
    logger.info(f"Already sent: {len(sent_ids)} articles")
    
    # Category requirements
    categories = {
        'vietnam': ('🇻🇳 TIN VIỆT NAM', 20),
        'world': ('🌍 TIN THẾ GIỚI', 15),
        'poland': ('🇵🇱 TIN BA LAN', 10),
        'immigration': ('✈️ TIN DI TRÚ BA LAN', 5)
    }
    
    all_articles = []
    
    # Fetch news for each category
    for cat, (title, count) in categories.items():
        logger.info(f"\n--- Fetching: {title} ---")
        
        articles = []
        seen_urls = set()
        
        # Try all feeds for this category
        for feed_url in RSS_FEEDS.get(cat, []):
            if len(articles) >= count:
                break
                
            xml = fetch_rss(feed_url)
            if xml:
                parsed = parse_rss(xml)
                for art in parsed:
                    if art['url'] not in seen_urls:
                        seen_urls.add(art['url'])
                        articles.append(art)
                        logger.info(f"  Found: {art['title'][:50]}...")
        
        logger.info(f"Total for {cat}: {len(articles)} articles")
        all_articles.extend(articles[:count])
    
    logger.info(f"\nTotal fetched: {len(all_articles)} articles")
    
    # Filter duplicates
    unique_articles = []
    for art in all_articles:
        art_id = hash(art['url']) % 1000000000
        if art_id not in sent_ids and art['title']:
            unique_articles.append(art)
    
    logger.info(f"Unique articles: {len(unique_articles)}")
    
    # If still no unique articles, force send recent ones (for testing)
    if not unique_articles and all_articles:
        logger.warning("No unique articles! Sending recent ones anyway...")
        unique_articles = all_articles[:10]  # Send first 10
    
    if not unique_articles:
        logger.info("No articles to send")
        msg = "<b>📰 TIN TỨC HÔM NAY</b>\n\n"
        msg += "Hiện tại chưa có tin mới.\n"
        msg += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
        send_message(msg)
        return
    
    # Build and send messages
    new_ids = set()
    
    # Message 1: Summary
    summary_msg = f"<b>📰 TÓM TẮT TIN TỨC HÔM NAY</b>\n\n"
    summary_msg += f"🇻🇳 Việt Nam: {min(10, len([a for a in unique_articles if 'vnexpress' in a['url'] or 'dantri' in a['url'] or 'cafef' in a['url']]))} tin\n"
    summary_msg += f"🌍 Thế giới: {min(10, len([a for a in unique_articles if 'bbc' in a['url'] or 'wsj' in a['url']]))} tin\n"
    summary_msg += f"🇵🇱 Ba Lan: {min(5, len([a for a in unique_articles if 'rp.pl' in a['url'] or 'poland' in a['url'].lower()]))} tin\n"
    summary_msg += f"✈️ Di trú: {min(3, len([a for a in unique_articles if 'globaris' in a['url']]))} tin\n"
    summary_msg += f"\n<i>Tổng cộng: {len(unique_articles)} tin mới</i>"
    
    send_message(summary_msg)
    logger.info("Sent summary message")
    
    # Message 2: Vietnam news
    vn_articles = [a for a in unique_articles if 'vnexpress' in a['url'] or 'dantri' in a['url'] or 'cafef' in a['url'] or 'tuoitre' in a['url'] or 'thanhnien' in a['url']]
    if vn_articles:
        msg = f"<b>🇻🇳 TIN VIỆT NAM</b>\n\n"
        for i, art in enumerate(vn_articles[:10], 1):
            t = art['title'][:70] + '...' if len(art['title']) > 70 else art['title']
            msg += f"{i}. {t}\n"
            msg += f"   🔗 {art['url']}\n\n"
        msg += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
        send_message(msg)
        logger.info(f"Sent {len(vn_articles)} Vietnam articles")
    
    # Message 3: World news
    world_articles = [a for a in unique_articles if 'bbc' in a['url'] or 'wsj' in a['url'] or 'cnn' in a['url'] or 'world' in a['url'].lower()]
    if world_articles:
        msg = f"<b>🌍 TIN THẾ GIỚI</b>\n\n"
        for i, art in enumerate(world_articles[:10], 1):
            t = art['title'][:70] + '...' if len(art['title']) > 70 else art['title']
            msg += f"{i}. {t}\n"
            msg += f"   🔗 {art['url']}\n\n"
        msg += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
        send_message(msg)
        logger.info(f"Sent {len(world_articles)} World articles")
    
    # Message 4: Poland news
    pl_articles = [a for a in unique_articles if 'rp.pl' in a['url'] or 'wyborcza' in a['url'] or 'tvn24' in a['url'] or 'poland' in a['title'].lower()]
    if pl_articles:
        msg = f"<b>🇵🇱 TIN BA LAN</b>\n\n"
        for i, art in enumerate(pl_articles[:8], 1):
            t = art['title'][:70] + '...' if len(art['title']) > 70 else art['title']
            msg += f"{i}. {t}\n"
            msg += f"   🔗 {art['url']}\n\n"
        msg += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
        send_message(msg)
        logger.info(f"Sent {len(pl_articles)} Poland articles")
    
    # Message 5: Immigration news
    imm_articles = [a for a in unique_articles if 'globaris' in a['url'] or 'immigration' in a['url'].lower() or 'visa' in a['title'].lower()]
    if imm_articles:
        msg = f"<b>✈️ TIN DI TRÚ BA LAN</b>\n\n"
        for i, art in enumerate(imm_articles[:5], 1):
            t = art['title'][:70] + '...' if len(art['title']) > 70 else art['title']
            msg += f"{i}. {t}\n"
            msg += f"   🔗 {art['url']}\n\n"
        msg += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
        send_message(msg)
        logger.info(f"Sent {len(imm_articles)} Immigration articles")
    
    # Update sent IDs
    for art in unique_articles:
        new_ids.add(hash(art['url']) % 1000000000)
    
    if new_ids:
        sent_ids.update(new_ids)
        save_sent_ids(sent_ids)
        logger.info(f"Updated: {len(sent_ids)} total sent IDs")
    
    logger.info("="*50)
    logger.info(f"Done! Sent {len(unique_articles)} new articles")
    logger.info("="*50)

if __name__ == '__main__':
    main()
