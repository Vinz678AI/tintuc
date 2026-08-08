#!/usr/bin/env python3
"""
Telegram News Bot - TIN TỨC TIẾNG VIỆT (TỔNG HỢP)
- Chỉ cần 3 secrets: BOT_TOKEN, CHAT_ID, GIST_ID
- TẤT CẢ tin bằng TIẾNG VIỆT (VN + World + Ba Lan)
- Không trùng lặp
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

# RSS Feeds - TIẾNG VIỆT + BA LAN
RSS_FEEDS = {
    'vietnam': [
        'https://vnexpress.net/rss/tin-moi-nhat.rss',
        'https://vnexpress.net/rss/tin-tuc.rss',
        'https://vnexpress.net/rss/market.rss',
        'https://vnexpress.net/rss/quoc-te.rss',
        'https://cafef.vn/rss/homepage.cafef',
        'https://nhipcaudautu.vn/rss/tintuc.rss',
        'https://tuoitre.vn/rss/tin-moi-nhat.rss',
        'https://thanhnien.vn/rss/latest.rss'
    ],
    'world': [
        'https://rsshub.app/bbc/vietnamese',
        'https://rsshub.app/voa/vietnamese'
    ],
    'poland': [
        'https://vnexpress.net/rss/quoc-te.rss'
    ],
    'immigration': [
        'https://vnexpress.net/rss/quoc-te.rss'
    ]
}

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
                articles.append({
                    'title': title.text.strip(),
                    'url': link.text.strip()
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
    logger.info("Starting Vietnamese News Bot...")
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
    
    # Filter duplicates
    unique_articles = [a for a in all_articles if hash(a['url']) % 1000000000 not in sent_ids and a['title']]
    logger.info(f"Unique articles: {len(unique_articles)}")
    
    if not unique_articles:
        msg = "<b>📰 TIN TỨC HÔM NAY</b>\n\n"
        msg += "✅ Đã kiểm tra nhưng KHÔNG CÓ TIN MỚI hôm nay.\n"
        msg += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
        send_message(msg)
        return
    
    # Group articles by category
    vn_articles = [a for a in unique_articles if any(d in a['url'] for d in ['vnexpress', 'cafef', 'nhipcaudautu', 'tuoitre', 'thanhnien'])]
    bbc_articles = [a for a in unique_articles if 'bbc' in a['url']]
    voa_articles = [a for a in unique_articles if 'voa' in a['url']]
    poland_articles = [a for a in unique_articles if any(k in a['title'].lower() for k in ['ba lan', 'poland', 'warsaw', 'krakow'])]
    
    # Remove poland from world if already categorized
    world_articles = [a for a in bbc_articles + voa_articles if a not in poland_articles]
    
    logger.info(f"Vietnam: {len(vn_articles)}, World: {len(world_articles)}, Poland: {len(poland_articles)}")
    
    new_ids = set()
    messages = []
    
    # Summary
    summary = f"<b>📰 TIN TỨC HÔM NAY</b>\n\n"
    summary += f"🇻🇳 Việt Nam: {len(vn_articles)} tin\n"
    summary += f"🌍 Thế giới: {len(world_articles)} tin\n"
    summary += f"🇵🇱 Ba Lan: {len(poland_articles)} tin\n"
    summary += f"\n<i>Tổng: {len(unique_articles)} tin mới</i>\n"
    summary += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
    messages.append(summary)
    
    # Vietnam news
    if vn_articles:
        msg = "<b>🇻🇳 TIN VIỆT NAM</b>\n\n"
        for i, art in enumerate(vn_articles[:15], 1):
            t = art['title'][:75] + '...' if len(art['title']) > 75 else art['title']
            msg += f"{i}. {t}\n"
            msg += f"🔗 {art['url']}\n\n"
            new_ids.add(hash(art['url']) % 1000000000)
        msg += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
        messages.append(msg)
    
    # World news (excluding Poland)
    if world_articles:
        msg = "<b>🌍 TIN THẾ GIỚI</b>\n\n"
        for i, art in enumerate(world_articles[:10], 1):
            t = art['title'][:75] + '...' if len(art['title']) > 75 else art['title']
            msg += f"{i}. {t}\n"
            msg += f"🔗 {art['url']}\n\n"
            new_ids.add(hash(art['url']) % 1000000000)
        msg += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
        messages.append(msg)
    
    # Poland news
    if poland_articles:
        msg = "<b>🇵🇱 TIN BA LAN</b>\n\n"
        for i, art in enumerate(poland_articles[:8], 1):
            t = art['title'][:75] + '...' if len(art['title']) > 75 else art['title']
            msg += f"{i}. {t}\n"
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
