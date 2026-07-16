#!/usr/bin/env python3
"""
led_sign.py - Control a Maplin N01GA (AM03127 / AM004-03127) 7x80 LED
moving-message display over a USB-to-serial adapter.

Protocol: 9600 baud, 8 data bits, no parity, 1 stop bit.
Packet:   <IDxx> payload CHECKSUM <E>
          where CHECKSUM is the XOR of every character in the payload,
          written as two uppercase hex digits. The sign replies "ACK".

Usage examples:
    python led_sign.py --list-ports
    python led_sign.py --port COM3 "HELLO WORLD"
    python led_sign.py --port COM3 --lead F --wait E "SALE TODAY"
    python led_sign.py --port COM3 --page B "Second message"
    python led_sign.py --port COM3 --run-pages AB
    python led_sign.py --port COM3 --set-clock
    python led_sign.py --port COM3 "Time now <KT>"
    python led_sign.py --port COM3 --brightness B
    python led_sign.py --port COM3 --delete-all
"""

import argparse
import sys
import time
from datetime import datetime

import serial
import serial.tools.list_ports

# Leading effect (<Fx> before the message) -- how the text arrives
LEAD_EFFECTS = {
    'A': 'immediate',      'B': 'x-open',        'C': 'curtain up',
    'D': 'curtain down',   'E': 'scroll left',   'F': 'scroll right',
    'G': 'v-open',         'H': 'v-close',       'I': 'scroll up',
    'J': 'scroll down',    'K': 'hold',          'L': 'snow',
    'M': 'twinkle',        'N': 'block move',    'P': 'random',
    'Q': 'pen "hello world"', 'R': 'pen "welcome"', 'S': 'pen "Amplus"',
}

# Lagging effect (<Fx> after the message) -- how the text leaves
LAG_EFFECTS = {k: v for k, v in LEAD_EFFECTS.items() if k in 'ABCDEFGHIJK'}

# Waiting time between lead and lag effect: A=0.5s, B=1s, C=2s ... Z=25s
WAIT_TIMES = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

# Display method/speed (<Mx>). Four letter groups = four speeds, and the
# position within each group is the style (decoded on real N01GA hardware):
#   group:    A-E / Q-U = fast scroll,  a-e / q-u = slow scroll
#   position: 1st (A/Q/a/q) = normal, 2nd (B/R/b/r) = blinking,
#             3rd-5th = songs 1-3 (the sign beeps tunes while holding)
DISPLAY_METHODS = 'ABCDEQRSTUabcdeqrstu'

# The sign's extended character set (sent as <Uxx> codes). Only the
# common ones are mapped here; see the AM03127 manual for the full table.
CHAR_MAP = {
    '£': '<U23>', '¢': '<U22>', '¥': '<U25>', '€': '<U00>',
    '©': '<U29>', '®': '<U2E>', '°': '<U3A>', '½': '<U3D>', '¼': '<U3C>',
    '→': '<U26>', '←': '<U27>', '↑': '<U01>', '↓': '<U02>',
}


class LedSign:
    """A Maplin N01GA / AM03127 LED sign on a serial port."""

    def __init__(self, port, sign_id=1, timeout=2.0):
        self.sign_id = sign_id
        self.ser = serial.Serial(
            port=port,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
        )

    def close(self):
        self.ser.close()

    @staticmethod
    def checksum(payload):
        cs = 0
        for c in payload:
            cs ^= ord(c)
        return format(cs, '02X')

    def send(self, payload):
        """Wrap payload in <IDxx>...checksum<E>, send it, return True on ACK."""
        packet = '<ID%02X>%s%s<E>' % (self.sign_id, payload, self.checksum(payload))
        self.ser.reset_input_buffer()
        self.ser.write(packet.encode('latin-1'))
        # Sign ID 00 is broadcast and never ACKs
        if self.sign_id == 0:
            return True
        reply = self.ser.read(3).decode('ascii', errors='replace')
        return reply == 'ACK'

    def set_page(self, text, page='A', lead='E', method='q', wait='C', lag='E'):
        """Store a message on a page. Page 'A' plays by default."""
        for ch, code in CHAR_MAP.items():
            text = text.replace(ch, code)
        payload = '<L1><P%s><F%s><M%s><W%s><F%s>%s' % (
            page, lead, method, wait, lag, text)
        return self.send(payload)

    def run_pages(self, pages='A'):
        """Set which page(s) play when no schedule is active, e.g. 'A' or 'ABC'."""
        if len(pages) == 1:
            return self.send('<RP%s>' % pages)
        # More than one page needs a schedule slot (A-E), running forever
        # schedule A: start yymmddHHMM, end yymmddHHMM, then the page list
        payload = '<TA>00010100009912312359%s' % pages
        return self.send(payload)

    def set_clock(self):
        """Set the sign's real-time clock to the PC's local time."""
        now = datetime.now()
        payload = now.strftime('<SC>%y0%w%m%d%H%M%S')
        return self.send(payload)

    def brightness(self, level='A'):
        """A=100%, B=75%, C=50%, D=25%."""
        return self.send('<B%s>' % level)

    def delete_all(self):
        """Wipe every page, schedule and graphic from the sign."""
        return self.send('<D*>')

    def set_id(self, new_id):
        """Assign a sign ID (1-255). Sent raw, without checksum, to all signs."""
        data = '<ID><%02X><E>' % new_id
        self.ser.reset_input_buffer()
        self.ser.write(data.encode('ascii'))
        reply = self.ser.read(2).decode('ascii', errors='replace')
        return reply == '%02X' % new_id


def list_ports():
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print('No serial ports found. Is the USB cable plugged in and its driver installed?')
        return
    for p in ports:
        print('%-8s %s' % (p.device, p.description))


def main():
    ap = argparse.ArgumentParser(
        description='Control a Maplin N01GA (AM03127) LED display.',
        epilog='Inline codes you can put in the message: <KT> time, <KD> date, '
               '<AA>-<AE> font size/style. Effects: ' +
               ', '.join('%s=%s' % kv for kv in LEAD_EFFECTS.items()))
    ap.add_argument('message', nargs='?', help='text to display')
    ap.add_argument('--port', help='serial port, e.g. COM3')
    ap.add_argument('--list-ports', action='store_true', help='list serial ports and exit')
    ap.add_argument('--id', type=int, default=1, help='sign ID (default 1, 0 = broadcast/no ACK)')
    ap.add_argument('--page', default='A', choices=list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
                    help='page to store the message on (default A)')
    ap.add_argument('--lead', default='E', choices=sorted(LEAD_EFFECTS),
                    help='leading effect (default E = scroll left)')
    ap.add_argument('--lag', default='E', choices=sorted(LAG_EFFECTS),
                    help='lagging effect (default E = scroll left)')
    ap.add_argument('--method', default='q', choices=sorted(set(DISPLAY_METHODS)),
                    help='display style+speed: A/Q=normal fast, a/q=normal slow '
                         '(default), B/R/b/r=blinking, others play songs/beeps')
    ap.add_argument('--wait', default='C', choices=list(WAIT_TIMES),
                    help='hold time between effects: A=0.5s B=1s C=2s ... Z=25s')
    ap.add_argument('--run-pages', metavar='PAGES',
                    help="page sequence to play, e.g. A or ABC")
    ap.add_argument('--set-clock', action='store_true', help="set the sign's clock to PC time")
    ap.add_argument('--brightness', choices=list('ABCD'),
                    help='A=100%% B=75%% C=50%% D=25%%')
    ap.add_argument('--delete-all', action='store_true', help='erase everything on the sign')
    ap.add_argument('--set-id', type=int, metavar='N', help='assign sign ID N (1-255)')
    args = ap.parse_args()

    if args.list_ports:
        list_ports()
        return

    if not args.port:
        ap.error('--port is required (use --list-ports to find it)')

    sign = LedSign(args.port, sign_id=args.id)
    try:
        did_something = False

        if args.set_id is not None:
            ok = sign.set_id(args.set_id)
            print('Set ID: %s' % ('OK' if ok else 'no reply'))
            did_something = True
        if args.delete_all:
            ok = sign.delete_all()
            print('Delete all: %s' % ('OK' if ok else 'no ACK'))
            did_something = True
        if args.set_clock:
            ok = sign.set_clock()
            print('Set clock: %s' % ('OK' if ok else 'no ACK'))
            did_something = True
        if args.brightness:
            ok = sign.brightness(args.brightness)
            print('Brightness: %s' % ('OK' if ok else 'no ACK'))
            did_something = True
        if args.message:
            ok = sign.set_page(args.message, page=args.page, lead=args.lead,
                               method=args.method, wait=args.wait, lag=args.lag)
            print('Page %s ("%s"): %s' % (args.page, args.message, 'OK' if ok else 'no ACK'))
            did_something = True
        if args.run_pages:
            ok = sign.run_pages(args.run_pages)
            print('Run pages %s: %s' % (args.run_pages, 'OK' if ok else 'no ACK'))
            did_something = True

        if not did_something:
            ap.error('nothing to do - give a message or an option')
    finally:
        sign.close()


if __name__ == '__main__':
    main()
