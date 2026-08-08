#!/usr/bin/env python3
"""
Telegram News Bot - NO DUPLICATES (Simple Version)
- Chỉ cần 3 secrets: BOT_TOKEN, CHAT_ID, GIST_ID
- KHÔNG cần GIST_TOKEN (dùng public gist)
- KHÔNG cần API key
- Tin thực từ RSS, không trùng lặp hoàn toàn
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

# RSS Feeds
RSS_FEEDS = {
    'vietnam': ['https://e.vnexpress.net/rss/news.rss', 'https://rss.vietnamnet.vn/rss/vn.rss'],
    'world': ['https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en'],
    'poland': ['https://rp.pl/rss_main'],
    'immigration': ['https://news.globarisconsulting.com/country/poland']
}

def fetch_rss(url):
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        return urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
    except:
        return None

def parse_rss(xml):
    articles = []
    try:
        root = ET.fromstring(xml)
        for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
            title = entry.find('{http://www.w3.org/2005/Atom}title')
            link = entry.find('{http://www.w3.org/2005/Atom}link')
            if title is not None and link is not None:
                articles.append({'title': title.text.strip(), 'url': link.get('href', '').strip()})
        if not articles:
            for item in root.findall('.//item'):
                title = item.find('title')
                link = item.find('link')
                if title is not None and link is not None:
                    articles.append({'title': title.text.strip(), 'url': link.text.strip()})
    except:
        pass
    return articles

def load_sent_ids():
    """Load sent IDs from Gist (public, no token needed)"""
    if not GIST_ID:
        return set()
    
    try:
        gist_url = f"https://gist.githubusercontent.com/{GIST_ID}/raw/sent_ids.json"
        req = Request(gist_url, headers={'User-Agent': 'NewsBot'})
        content = urlopen(req, timeout=10).read().decode('utf-8')
        ids = json.loads(content)
        logger.info(f"Loaded {len(ids)} sent IDs from Gist")
        return set(ids)
    except:
        return set()

def save_sent_ids(sent_ids):
    """Save sent IDs to Gist"""
    if not GIST_ID:
        return
    
    # Try with GitHub API (may work if gist is public)
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
    except:
        # If fails, save locally
        with open('sent_ids.json', 'w') as f:
            json.dump(list(sent_ids), f)
        logger.info(f"Saved {len(sent_ids)} IDs locally (Gist save failed)")

def fetch_news(category, max_items):
    """Fetch news from RSS"""
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
        return urlopen(req, timeout=10).read().decode()
    except Exception as e:
        logger.error(f"Send error: {e}")
        return None

def main():
    logger.info("Starting news bot...")
    
    # Load previously sent IDs
    sent_ids = load_sent_ids()
    
    categories = {
        'vietnam': ('🇻🇳 TIN VIỆT NAM', 10),
        'world': ('🌍 TIN THẾ GIỚI', 20),
        'poland': ('🇵🇱 TIN BA LAN', 10),
        'immigration': ('✈️ TIN DI TRÚ BA LAN', 5)
    }
    
    all_new_ids = set()
    
    for cat, (title, count) in categories.items():
        articles = fetch_news(cat, count * 2)  # Fetch extra to filter duplicates
        unique_articles = []
        
        for art in articles:
            art_id = hash(art['url']) % 1000000000
            if art_id not in sent_ids and art['title']:
                unique_articles.append(art)
                all_new_ids.add(art_id)
            
            if len(unique_articles) >= count:
                break
        
        if unique_articles:
            msg = f"<b>{title}</b>\n<i>{len(unique_articles)}/{len(articles)} tin MỚI</i>\n\n"
            for i, art in enumerate(unique_articles, 1):
                t = art['title'][:90] + '...' if len(art['title']) > 90 else art['title']
                msg += f"<b>{i}. {t}</b>\n🔗 {art['url'][:120]}\n\n"
            msg += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
            
            logger.info(f"Sending {len(unique_articles)} articles for {title}")
            send_message(msg)
    
    # Update sent IDs
    if all_new_ids:
        sent_ids.update(all_new_ids)
        save_sent_ids(sent_ids)
        logger.info(f"Updated: {len(sent_ids)} total sent IDs")
    
    logger.info("Done!")

if __name__ == '__main__':
    main()
