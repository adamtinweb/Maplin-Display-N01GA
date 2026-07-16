#!/usr/bin/env python3
"""
trains.py - Next train departures on the Maplin N01GA LED display.

Page A: next Elizabeth line train from Harold Wood towards London
        Liverpool Street (live from the TfL Unified API, no key needed).
Page B: next Looe Valley Line train from Looe to Liskeard (live National
        Rail data via the Huxley2 public Darwin proxy).

The sign cycles the pages with a vertical scroll (scroll up in/out),
holding each for 5 seconds; the data refreshes every minute.

Usage:
    python trains.py --port COM11
    python trains.py --dry-run --once
"""

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime

from led_sign import LedSign

PAGE_WAIT = 'F'            # 5 seconds per page before scrolling on

# --- Harold Wood -> Liverpool Street (TfL) -------------------------------

TFL_STOP_ID = '910GHRLDWOD'    # Harold Wood Rail Station
TFL_LINE = 'elizabeth'
# Trains from Harold Wood that do NOT pass Liverpool Street: eastbound to
# Shenfield/Brentwood, or short westbound terminators at Gidea Park/Romford.
TFL_EXCLUDE = ('Shenfield', 'Brentwood', 'Gidea Park', 'Romford')


def http_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return json.load(urllib.request.urlopen(req, timeout=20))


def next_harold_wood():
    """'HH:MM' of the next London-bound Elizabeth line train, or None."""
    url = 'https://api.tfl.gov.uk/Line/%s/Arrivals/%s' % (TFL_LINE, TFL_STOP_ID)
    trains = [a for a in http_json(url)
              if not any(x in (a.get('destinationName') or '')
                         for x in TFL_EXCLUDE)]
    if not trains:
        return None
    soonest = min(trains, key=lambda a: a['timeToStation'])
    when = datetime.fromisoformat(soonest['expectedArrival']).astimezone()
    return when.strftime('%H:%M')


# --- Looe -> Liskeard (National Rail via Huxley2) -------------------------

def next_looe():
    """'HH:MM' of the next Looe Valley Line departure, or None."""
    board = http_json('https://huxley2.azurewebsites.net/departures/LOO/to/LSK/1')
    services = board.get('trainServices') or []
    if not services:
        return None
    s = services[0]
    etd = s.get('etd') or ''
    # etd is 'On time', a revised 'HH:MM', 'Delayed' or 'Cancelled'.
    # 'DLYD'/'CANX' keep the page inside the sign's ~13 character width.
    if ':' in etd:
        return etd
    if etd.lower() == 'delayed':
        return 'DLYD'
    if etd.lower() == 'cancelled':
        return 'CANX'
    return s.get('std')


# --- the sign --------------------------------------------------------------

# (route label using CRS codes, fetcher). The sign fits ~13 characters and
# the arrow is a single character in its extended set: 'HRO→LST 08:14'.
SERVICES = [
    ('HRO→LST', next_harold_wood),
    ('LOO→LSK', next_looe),
]


def build_pages():
    pages = []
    for label, fetch in SERVICES:
        try:
            when = fetch()
        except Exception as e:
            print('%s fetch failed: %s' % (label, e))
            when = None
        pages.append('%s %s' % (label, when or 'NONE'))
    return pages


def update_sign(sign, pages):
    """Write the pages and have the sign vertical-scroll between them."""
    ok = True
    for page_id, text in zip('ABCDEF', pages):
        ok &= sign.set_page(text, page=page_id, lead='I', method='q',
                            wait=PAGE_WAIT, lag='I')
    ok &= sign.run_pages('ABCDEF'[:len(pages)])
    return ok


def main():
    sys.stdout.reconfigure(errors='replace')

    ap = argparse.ArgumentParser(
        description='Next-train departure board for the LED sign.')
    ap.add_argument('--port', help='serial port, e.g. COM11')
    ap.add_argument('--id', type=int, default=1, help='sign ID (default 1)')
    ap.add_argument('--interval', type=int, default=60,
                    help='seconds between data refreshes (default 60)')
    ap.add_argument('--once', action='store_true', help='update once and exit')
    ap.add_argument('--dry-run', action='store_true',
                    help='print the pages instead of sending them')
    args = ap.parse_args()

    if not args.dry_run and not args.port:
        ap.error('--port is required unless --dry-run')

    sign = None
    try:
        while True:
            pages = build_pages()
            stamp = time.strftime('%H:%M:%S')
            if args.dry_run:
                print('[%s] %s' % (stamp, ' / '.join(pages)))
            else:
                if sign is None:
                    sign = LedSign(args.port, sign_id=args.id)
                ok = update_sign(sign, pages)
                print('[%s] %s -- %s' % (stamp, 'sent OK' if ok else 'NO ACK',
                                         ' / '.join(pages)))
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
