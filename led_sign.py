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

# 5x7 pixel font (rows top to bottom, 5 bits per row, MSB = left pixel)
# used to build the 180-degree rotated character set for upside-down
# mounting. The AM03127 <Fsxy> command can redefine the European char
# table slots <U40>..<U7F> with custom glyphs.
FONT_5X7 = {
    '0': (0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110),
    '1': (0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    '2': (0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111),
    '3': (0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110),
    '4': (0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010),
    '5': (0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110),
    '6': (0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110),
    '7': (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000),
    '8': (0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110),
    '9': (0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100),
    'A': (0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    'B': (0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110),
    'C': (0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110),
    'D': (0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110),
    'E': (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111),
    'F': (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000),
    'G': (0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01111),
    'H': (0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    'I': (0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    'J': (0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100),
    'K': (0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001),
    'L': (0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111),
    'M': (0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001),
    'N': (0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001),
    'O': (0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    'P': (0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000),
    'Q': (0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101),
    'R': (0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001),
    'S': (0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110),
    'T': (0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    'U': (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    'V': (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100),
    'W': (0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b10101, 0b01010),
    'X': (0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001),
    'Y': (0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100),
    'Z': (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111),
    ':': (0b00000, 0b01100, 0b01100, 0b00000, 0b01100, 0b01100, 0b00000),
    '-': (0b00000, 0b00000, 0b00000, 0b11111, 0b00000, 0b00000, 0b00000),
    '.': (0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b01100, 0b01100),
    ',': (0b00000, 0b00000, 0b00000, 0b00000, 0b01100, 0b00100, 0b01000),
    '!': (0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00000, 0b00100),
    '?': (0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b00000, 0b00100),
    '/': (0b00000, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b00000),
    "'": (0b01100, 0b00100, 0b01000, 0b00000, 0b00000, 0b00000, 0b00000),
}


def _rotate_glyph(rows):
    """Rotate a 5x7 glyph 180 degrees: reverse row order, mirror each row."""
    return tuple(int(format(r, '05b')[::-1], 2) for r in reversed(rows))


# Effects that look wrong when the sign hangs upside down, and what to use
# instead so the apparent motion stays the same.
FLIP_EFFECTS = {'C': 'D', 'D': 'C', 'E': 'F', 'F': 'E', 'I': 'J', 'J': 'I'}

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

    def send(self, payload, _retried=False):
        """Wrap payload in <IDxx>...checksum<E>, send it, return True on ACK."""
        packet = '<ID%02X>%s%s<E>' % (self.sign_id, payload, self.checksum(payload))
        self.ser.reset_input_buffer()
        self.ser.write(packet.encode('latin-1'))
        # Sign ID 00 is broadcast and never ACKs
        if self.sign_id == 0:
            return True
        reply = self.ser.read(3).decode('ascii', errors='replace')
        if reply == 'ACK':
            return True
        if not _retried:
            # the sign forgets its ID when it loses power and then ignores
            # everything addressed to it -- re-teach the ID and retry once
            self.set_id(self.sign_id)
            return self.send(payload, _retried=True)
        return False

    def install_flipped_font(self):
        """Upload 180-degree rotated glyphs into the sign's redefinable
        European character slots <U40>+. Call once before flip_text()."""
        self.flip_slots = {}
        all_ok = True
        for i, ch in enumerate(sorted(FONT_5X7)):
            rows = _rotate_glyph(FONT_5X7[ch])
            # <FAxy>: redefine 5x7 char at slot xy; 8 data bytes, each row
            # left-aligned (5-bit row in bits 7..3), padded to 8 with 0x00
            data = ''.join(chr(r << 3) for r in rows) + '\x00'
            packet = '<FA%02X>' % i + data
            if not self.send(packet):
                # the sign sometimes needs a breather between flash writes
                time.sleep(0.3)
                all_ok &= self.send(packet)
            self.flip_slots[ch] = 0x40 + i
            time.sleep(0.1)
        return all_ok

    def flip_text(self, text):
        """Convert text for a sign hung upside down: reverse the string and
        map characters to the rotated glyphs from install_flipped_font()."""
        out = []
        for ch in reversed(text.upper()):
            if ch in self.flip_slots:
                out.append('<U%02X>' % self.flip_slots[ch])
            elif ch == '→':
                out.append('←')   # the factory arrows are each other rotated
            elif ch == '←':
                out.append('→')
            else:
                out.append(ch)    # space and unknown chars pass through
        return ''.join(out)

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
