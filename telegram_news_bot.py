#!/usr/bin/env python3
"""
Telegram News Bot - TIN TỨC TIẾNG VIỆT (No Duplicates)
- Chỉ cần 3 secrets: BOT_TOKEN, CHAT_ID, GIST_ID
- KHÔNG cần GIST_TOKEN (dùng public gist)
- KHÔNG cần API key
- Tin tiếng Việt từ các nguồn Việt Nam
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

def load_sent_ids():
    """Load sent IDs from Gist"""
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
        with open('sent_ids.json', 'w') as f:
            json.dump(list(sent_ids), f)
        logger.info(f"Saved {len(sent_ids)} IDs locally")

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
    
    sent_ids = load_sent_ids()
    
    categories = {
        'vietnam': ('🇻🇳 TIN VIỆT NAM', 10),
        'world': ('🌍 TIN THẾ GIỚI', 20),
        'poland': ('🇵🇱 TIN BA LAN', 10),
        'immigration': ('✈️ TIN DI TRÚ BA LAN', 5)
    }
    
    all_new_ids = set()
    
    for cat, (title, count) in categories.items():
        articles = fetch_news(cat, count * 2)
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
    
    if all_new_ids:
        sent_ids.update(all_new_ids)
        save_sent_ids(sent_ids)
        logger.info(f"Updated: {len(sent_ids)} total sent IDs")
    
    logger.info("Done!")

if __name__ == '__main__':
    main()
