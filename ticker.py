#!/usr/bin/env python3
"""
ticker.py - FTSE-style scrolling ticker for the Maplin N01GA LED display.

Shows live prices for Expedia, Bitcoin and three LSE ETFs (via Yahoo
Finance's public chart API) plus the current top BBC News headline (via
their RSS feed), and refreshes the sign at a fixed interval.

Usage:
    python ticker.py --port COM11              # run forever, refresh 5 min
    python ticker.py --port COM11 --once       # send one update and exit
    python ticker.py --dry-run                 # print the message, no sign
"""

import argparse
import json
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

from led_sign import LedSign

# (Yahoo Finance symbol, name shown on the ticker)
QUOTES = [
    ('EXPE',    'EXPE'),
    ('BTC-GBP', 'BTC'),
    ('ISF.L',   'ISF'),    # iShares Core FTSE 100 ETF GBP Dist
    ('VUAG.L',  'VUAG'),   # Vanguard S&P 500 ETF Acc
    ('XNAQ.L',  'XNAQ'),   # Xtrackers Nasdaq 100 ETF
]

BBC_RSS = 'https://feeds.bbci.co.uk/news/rss.xml'
SEPARATOR = '  *  '


def http_get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, timeout=15).read()


def fetch_quote(symbol):
    """Return (price, previous_close, currency) from Yahoo Finance."""
    url = ('https://query1.finance.yahoo.com/v8/finance/chart/'
           '%s?range=1d&interval=1d' % symbol)
    meta = json.loads(http_get(url))['chart']['result'][0]['meta']
    return (meta['regularMarketPrice'],
            meta.get('chartPreviousClose') or meta.get('previousClose'),
            meta.get('currency', ''))


def format_quote(name, price, prev, currency):
    """One ticker segment, e.g. 'EXPE $267.11 ^0.3%'."""
    if currency == 'GBp':               # LSE quotes in pence
        value = '%.1fp' % price
    elif currency == 'GBP':
        value = '£%.0f' % price if price >= 1000 else '£%.2f' % price
    elif currency == 'USD':
        value = '$%.2f' % price
    else:
        value = '%.2f %s' % (price, currency)

    segment = '%s %s' % (name, value)
    if prev:
        pct = (price - prev) / prev * 100
        arrow = '↑' if pct >= 0 else '↓'   # sign's built-in arrow glyphs
        segment += ' %s%.1f%%' % (arrow, abs(pct))
    return segment


def fetch_headline():
    """Top item title from the BBC News RSS feed."""
    root = ET.fromstring(http_get(BBC_RSS))
    title = root.find('./channel/item/title')
    return title.text.strip() if title is not None and title.text else None


def build_message():
    parts = []
    for symbol, name in QUOTES:
        try:
            parts.append(format_quote(name, *fetch_quote(symbol)))
        except Exception as e:
            print('quote %s failed: %s' % (symbol, e))
            parts.append('%s ?' % name)
    try:
        headline = fetch_headline()
        if headline:
            parts.append('BBC: %s' % headline)
    except Exception as e:
        print('BBC feed failed: %s' % e)
    return SEPARATOR.join(parts)


def main():
    # the Windows console may not be UTF-8; don't crash printing ↑/↓/£
    sys.stdout.reconfigure(errors='replace')

    ap = argparse.ArgumentParser(description='LED sign stock/news ticker.')
    ap.add_argument('--port', help='serial port, e.g. COM11')
    ap.add_argument('--id', type=int, default=1, help='sign ID (default 1)')
    ap.add_argument('--interval', type=int, default=300,
                    help='seconds between refreshes (default 300)')
    ap.add_argument('--method', default='q',
                    help='display method letter (default q = normal, slow)')
    ap.add_argument('--once', action='store_true', help='update once and exit')
    ap.add_argument('--dry-run', action='store_true',
                    help='print the ticker text instead of sending it')
    args = ap.parse_args()

    if not args.dry_run and not args.port:
        ap.error('--port is required unless --dry-run')

    sign = None
    try:
        while True:
            message = build_message()
            stamp = time.strftime('%H:%M:%S')
            if args.dry_run:
                print('[%s] %s' % (stamp, message))
            else:
                if sign is None:
                    sign = LedSign(args.port, sign_id=args.id)
                # scroll in and out continuously, minimal hold: ticker style
                ok = sign.set_page(message, page='A', lead='E',
                                   method=args.method, wait='A', lag='E')
                print('[%s] %s -- %s' % (stamp, 'sent OK' if ok else 'NO ACK',
                                         message))
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        if sign is not None:
            sign.close()


if __name__ == '__main__':
    main()
