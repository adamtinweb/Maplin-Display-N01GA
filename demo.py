#!/usr/bin/env python3
"""
demo.py - Tour of every N01GA display effect, illustrated with famous quotes.

Walks through all 18 leading effects (and a variety of lagging effects and
hold times), sending one quote per effect and printing what to watch for.

Usage:
    python demo.py --port COM11
    python demo.py --port COM11 --loop      # repeat forever
    python demo.py --port COM11 --fast      # shorter pauses between items
"""

import argparse
import sys
import time

from led_sign import LedSign

# Each entry: (lead, lag, wait, text for the sign, note for the console).
# The sign fits ~13 characters without scrolling, so the static effects get
# short quotes and the scrolling effects (E, F, I, J) get full-length ones.
DEMOS = [
    ('A', 'B', 'D', 'CARPE DIEM',
     'A: appear instantly - "Carpe diem" (Horace)'),
    ('B', 'G', 'D', '2B OR NOT 2B',
     'B: X-open from centre - "To be, or not to be" (Shakespeare)'),
    ('C', 'D', 'D', 'ALL THE WORLD',
     'C: curtain up - "All the world\'s a stage" (Shakespeare)'),
    ('D', 'C', 'D', 'SWEET PRINCE',
     'D: curtain down - "Good night, sweet prince" (Shakespeare)'),
    ('E', 'E', 'B', 'The only thing we have to fear is fear itself - Roosevelt',
     'E: scroll left (classic ticker) - full quote scrolls through'),
    ('F', 'F', 'B', 'Float like a butterfly, sting like a bee - Ali',
     'F: scroll right - full quote scrolls through backwards'),
    ('G', 'H', 'D', 'EUREKA!',
     'G: V-open - "Eureka!" (Archimedes)'),
    ('H', 'G', 'D', "I'LL BE BACK",
     'H: V-close - "I\'ll be back" (The Terminator)'),
    ('I', 'I', 'B', 'One small step for man, one giant leap for mankind - Armstrong',
     'I: scroll up - full quote'),
    ('J', 'J', 'B', 'What goes up must come down - Newton',
     'J: scroll down - full quote'),
    ('K', 'A', 'K', 'STAY HUNGRY',
     'K: hold - "Stay hungry, stay foolish" (Steve Jobs)'),
    ('L', 'D', 'F', 'LET IT SNOW',
     'L: snow - pixels sprinkle in - "Let it snow" (Sammy Cahn)'),
    ('M', 'H', 'F', 'LITTLE STAR',
     'M: twinkle - "Twinkle, twinkle, little star" (Jane Taylor)'),
    ('N', 'B', 'D', 'BIT BY BIT',
     'N: block move - "Rome wasn\'t built in a day"'),
    ('P', 'J', 'D', 'PLAY DICE?',
     'P: random pixels - "God does not play dice" (Einstein)'),
    ('Q', 'E', 'C', 'ignored',
     'Q: pen-writing demo - the sign hand-writes "hello world"'),
    ('R', 'E', 'C', 'ignored',
     'R: pen-writing demo - the sign hand-writes "welcome"'),
    ('S', 'E', 'C', 'ignored',
     'S: pen-writing demo - the sign hand-writes "Amplus"'),
]

WAIT_SECONDS = {letter: max(0.5, i) for i, letter in
                enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}  # A=0.5, B=1, C=2...


def item_duration(lead, wait, text, fast):
    """Rough time to let an effect play out before sending the next one."""
    base = 4 if fast else 7                       # lead + lag animation time
    hold = WAIT_SECONDS.get(wait, 2)
    scroll = 0.25 * len(text) if lead in 'EFIJ' else 0
    return base + hold + scroll


def main():
    sys.stdout.reconfigure(errors='replace')

    ap = argparse.ArgumentParser(description='Show off every sign effect.')
    ap.add_argument('--port', required=True, help='serial port, e.g. COM11')
    ap.add_argument('--id', type=int, default=1, help='sign ID (default 1)')
    ap.add_argument('--loop', action='store_true', help='repeat forever')
    ap.add_argument('--fast', action='store_true',
                    help='fast display method and shorter pauses')
    args = ap.parse_args()

    method = 'Q' if args.fast else 'q'
    sign = LedSign(args.port, sign_id=args.id)
    try:
        while True:
            for lead, lag, wait, text, note in DEMOS:
                print(note)
                if not sign.set_page(text, page='A', lead=lead,
                                     method=method, wait=wait, lag=lag):
                    print('  (no ACK from sign)')
                time.sleep(item_duration(lead, wait, text, args.fast))
            if not args.loop:
                break
            print('--- again! ---')
    except KeyboardInterrupt:
        pass
    finally:
        sign.close()


if __name__ == '__main__':
    main()
