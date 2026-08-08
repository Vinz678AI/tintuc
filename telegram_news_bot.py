#!/usr/bin/env python3
"""
Telegram News Bot - TIN TỨC TIẾNG VIỆT (Tổng hợp)
- Chỉ cần 3 secrets: BOT_TOKEN, CHAT_ID, GIST_ID
- Tin TIẾNG VIỆT từ các nguồn Việt Nam
- Không trùng lặp với Gist
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
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')

if not BOT_TOKEN or not CHAT_ID:
    logger.error("Cần BOT_TOKEN và CHAT_ID")
    sys.exit(1)

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# RSS Feeds TIẾNG VIỆT
RSS_FEEDS = {
    'vietnam': [
        'https://vnexpress.net/rss/tin-moi-nhat.rss',
        'https://vnexpress.net/rss/tin-tuc.rss',
        'https://vnexpress.net/rss/market.rss',
        'https://cafef.vn/rss/homepage.cafef',
        'https://nhipcaudautu.vn/rss/tintuc.rss',
        'https://tuoitre.vn/rss/tin-moi-nhat.rss',
        'https://thanhnien.vn/rss/latest.rss'
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
    except:
        pass
    return articles

def load_sent_ids():
    """Load from Gist using API"""
    if not GIST_ID:
        return set()
    
    # Try reading from gist raw URL (works for public gists)
    try:
        gist_url = f"https://gist.githubusercontent.com/{GIST_ID}/raw/sent_ids.json"
        req = Request(gist_url, headers={'User-Agent': 'NewsBot'})
        content = urlopen(req, timeout=15).read().decode('utf-8')
        ids = json.loads(content)
        logger.info(f"Loaded {len(ids)} IDs from Gist raw URL")
        return set(ids)
    except Exception as e:
        logger.warning(f"Failed to load from Gist raw URL: {e}")
    
    # Try using API with token (for private gists)
    if GITHUB_TOKEN:
        try:
            gist_api = f"https://api.github.com/gists/{GIST_ID}"
            req = Request(gist_api, headers={
                'User-Agent': 'NewsBot',
                'Authorization': f'token {GITHUB_TOKEN}',
                'Accept': 'application/vnd.github.v3+json'
            })
            data = json.loads(urlopen(req, timeout=15).read().decode('utf-8'))
            for fname, fdata in data.get('files', {}).items():
                ids = json.loads(fdata.get('content', '[]'))
                logger.info(f"Loaded {len(ids)} IDs from Gist API")
                return set(ids)
        except Exception as e:
            logger.warning(f"Failed to load from Gist API: {e}")
    
    logger.info("No sent IDs found (empty list)")
    return set()

def save_sent_ids(sent_ids):
    """Save to Gist using API (requires token)"""
    if not GIST_ID or not GITHUB_TOKEN:
        logger.warning("Cannot save to Gist - no GIST_ID or GITHUB_TOKEN")
        return
    
    try:
        gist_url = f"https://api.github.com/gists/{GIST_ID}"
        payload = json.dumps({'files': {'sent_ids.json': {'content': json.dumps(list(sent_ids))}}}).encode()
        req = Request(
            gist_url,
            data=payload,
            headers={
                'User-Agent': 'NewsBot',
                'Authorization': f'token {GITHUB_TOKEN}',
                'Content-Type': 'application/json'
            },
            method='PATCH'
        )
        urlopen(req, timeout=15)
        logger.info(f"Saved {len(sent_ids)} IDs to Gist")
    except Exception as e:
        logger.error(f"Failed to save to Gist: {e}")
        # Save locally as fallback
        with open('sent_ids.json', 'w') as f:
            json.dump(list(sent_ids), f)
        logger.info("Saved to local file instead")

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
    logger.info(f"GIST_ID: {GIST_ID}")
    logger.info(f"GITHUB_TOKEN: {'SET' if GITHUB_TOKEN else 'NOT SET'}")
    logger.info("="*50)
    
    # Load sent IDs
    sent_ids = load_sent_ids()
    logger.info(f"Already sent: {len(sent_ids)} articles")
    
    # Fetch all articles
    all_articles = []
    seen_urls = set()
    
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
    unique_articles = []
    for art in all_articles:
        art_id = hash(art['url']) % 1000000000
        if art_id not in sent_ids and art['title']:
            unique_articles.append(art)
    
    logger.info(f"Unique articles: {len(unique_articles)}")
    
    # If no new articles, send notification
    if not unique_articles:
        logger.info("No new articles")
        msg = "<b>📰 TIN TỨC HÔM NAY</b>\n\n"
        msg += "✅ Đã kiểm tra nhưng KHÔNG CÓ TIN MỚI hôm nay.\n"
        msg += "⏰ " + datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')
        send_message(msg)
        return
    
    # Group by category
    vn_articles = [a for a in unique_articles if any(d in a['url'] for d in ['vnexpress', 'cafef', 'nhipcaudautu', 'tuoitre', 'thanhnien'])]
    world_articles = [a for a in unique_articles if 'bbc' in a['url'] or 'rsshub' in a['url']]
    pl_articles = [a for a in unique_articles if 'rp.pl' in a['url'] or 'poland' in a['url'].lower()]
    imm_articles = [a for a in unique_articles if 'globaris' in a['url'] or 'immigration' in a['title'].lower()]
    
    # Send messages
    new_ids = set()
    
    # Summary
    summary = f"<b>📰 TIN TỨC HÔM NAY</b>\n\n"
    summary += f"🇻🇳 Việt Nam: {len(vn_articles)} tin\n"
    summary += f"🌍 Thế giới: {len(world_articles)} tin\n"
    summary += f"🇵🇱 Ba Lan: {len(pl_articles)} tin\n"
    summary += f"✈️ Di trú: {len(imm_articles)} tin\n"
    summary += f"\n<i>Tổng: {len(unique_articles)} tin mới</i>"
    send_message(summary)
    
    # Vietnam news
    if vn_articles:
        msg = "<b>🇻🇳 TIN VIỆT NAM</b>\n\n"
        for i, art in enumerate(vn_articles[:15], 1):
            t = art['title'][:80] + '...' if len(art['title']) > 80 else art['title']
            msg += f"{i}. {t}\n"
            msg += f"🔗 {art['url']}\n\n"
            new_ids.add(hash(art['url']) % 1000000000)
        msg += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
        send_message(msg)
    
    # World news
    if world_articles:
        msg = "<b>🌍 TIN THẾ GIỚI</b>\n\n"
        for i, art in enumerate(world_articles[:15], 1):
            t = art['title'][:80] + '...' if len(art['title']) > 80 else art['title']
            msg += f"{i}. {t}\n"
            msg += f"🔗 {art['url']}\n\n"
            new_ids.add(hash(art['url']) % 1000000000)
        msg += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
        send_message(msg)
    
    # Poland news
    if pl_articles:
        msg = "<b>🇵🇱 TIN BA LAN</b>\n\n"
        for i, art in enumerate(pl_articles[:10], 1):
            t = art['title'][:80] + '...' if len(art['title']) > 80 else art['title']
            msg += f"{i}. {t}\n"
            msg += f"🔗 {art['url']}\n\n"
            new_ids.add(hash(art['url']) % 1000000000)
        msg += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
        send_message(msg)
    
    # Immigration news
    if imm_articles:
        msg = "<b>✈️ TIN DI TRÚ BA LAN</b>\n\n"
        for i, art in enumerate(imm_articles[:5], 1):
            t = art['title'][:80] + '...' if len(art['title']) > 80 else art['title']
            msg += f"{i}. {t}\n"
            msg += f"🔗 {art['url']}\n\n"
            new_ids.add(hash(art['url']) % 1000000000)
        msg += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}"
        send_message(msg)
    
    # Update sent IDs
    if new_ids:
        sent_ids.update(new_ids)
        save_sent_ids(sent_ids)
        logger.info(f"Updated: {len(sent_ids)} total IDs")
    
    logger.info(f"Done! Sent {len(unique_articles)} new articles")

if __name__ == '__main__':
    main()
