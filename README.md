# Maplin-Display-N01GA

A Python library and command-line app for controlling the **Maplin N01GA**
programmable LED moving-message display (7×80 red LED matrix) from a PC over
a USB-to-serial adapter.

The N01GA is the red-only sibling of the Maplin N00GA and is built on the
**Amplus AM03127 / AM004-03127** sign controller, so it speaks the
well-documented AM03127 serial protocol.

## Hardware

- **Data port:** RJ11 socket on the sign carrying RS232. Pinout facing the
  socket: GND (top pin), TXD, RXD.
- **Power:** 12 V DC.
- **PC side:** any USB-to-serial adapter presenting a COM port. Tested with a
  Silicon Labs CP210x bridge. Note that many of the original Maplin
  programming cables use a Prolific PL2303 chip; older PL2303HXA chips are
  rejected by the current Windows driver ("PHASED OUT SINCE 2012") and need
  the legacy v3.8.31.0 driver instead.
- **Serial settings:** 9600 baud, 8 data bits, no parity, 1 stop bit.

## Installation

Requires Python 3 and [pyserial](https://pypi.org/project/pyserial/):

```
pip install pyserial
```

## Usage

```
python led_sign.py --list-ports
python led_sign.py --port COM11 "HELLO WORLD"
python led_sign.py --port COM11 --lead L --wait G "Snow effect, hold 6s"
python led_sign.py --port COM11 --set-clock
python led_sign.py --port COM11 "Time is <KT>"
python led_sign.py --port COM11 --page B "Second message" --run-pages AB
python led_sign.py --port COM11 --brightness C
python led_sign.py --port COM11 --delete-all
```

If a command reports `no ACK`, the usual causes are the wrong COM port, a
sign whose ID is not 1 (fix with `--set-id 1`), or swapped TX/RX wiring.

It can also be used as a library:

```python
from led_sign import LedSign

sign = LedSign('COM11')
sign.set_page('Hello from Python', lead='E', wait='C')
sign.set_clock()
sign.close()
```

## Options

| Option | Values | Meaning |
|---|---|---|
| `--page` | `A`–`Z` | Which of the 26 message pages to write. Page `A` plays by default. |
| `--lead` | `A`–`S` | Leading effect (how the text arrives), see below. |
| `--lag` | `A`–`K` | Lagging effect (how the text leaves). |
| `--wait` | `A`–`Z` | Hold time between effects: `A`=0.5 s, `B`=1 s, `C`=2 s … `Z`=25 s. |
| `--method` | see below | Display style and scroll speed. |
| `--brightness` | `A`–`D` | `A`=100 %, `B`=75 %, `C`=50 %, `D`=25 %. |
| `--run-pages` | e.g. `A` or `ABC` | Page or page sequence to play. |
| `--set-clock` | | Set the sign's real-time clock to the PC's local time. |
| `--set-id` | 1–255 | Assign the sign an ID (broadcast, works on unconfigured signs). |
| `--delete-all` | | Erase all pages, schedules and graphics. |

**Leading effects** (`--lead`): `A` immediate, `B` x-open, `C` curtain up,
`D` curtain down, `E` scroll left, `F` scroll right, `G` v-open, `H` v-close,
`I` scroll up, `J` scroll down, `K` hold, `L` snow, `M` twinkle,
`N` block move, `P` random, `Q`/`R`/`S` pen-writing demos.
Lagging effects are the same set limited to `A`–`K`.

**Display method** (`--method`) — decoded by experiment on real N01GA
hardware, since no manual documents it fully. The four letter groups select
the scroll speed and the position within the group selects the style:

| Group | Speed |
|---|---|
| `A`–`E`, `Q`–`U` (uppercase) | fast |
| `a`–`e`, `q`–`u` (lowercase) | slow |

Within each group: 1st letter (`A`/`Q`/`a`/`q`) = normal, 2nd = blinking,
3rd–5th = built-in songs 1–3 (the sign beeps a tune while the text holds).
The default is `q` — normal style, slow scroll, no beeps.

**Inline codes** usable inside a message: `<KT>` live time, `<KD>` live date,
`<AA>`–`<AE>` font size/style. Common symbols such as `£ € ° © ½ →` are
translated automatically to the sign's extended character set (`<Uxx>` codes).

## Protocol notes

Every command is an ASCII packet:

```
<ID01>  payload  CS  <E>
```

where `CS` is the XOR of every byte in the payload, written as two uppercase
hex digits, and `01` is the sign ID (ID `00` broadcasts, with no reply). The
sign answers `ACK` on success. A text page payload looks like:

```
<L1><PA><FE><Mq><WC><FE>HELLO WORLD
 │    │    │    │   │    │
 │    │    │    │   │    └ lagging effect
 │    │    │    │   └ wait time
 │    │    │    └ display method / speed
 │    │    └ leading effect
 │    └ page A
 └ line 1 (the N01GA is single-line)
```

Other commands used by the app: `<SC>` set clock, `<Bx>` brightness,
`<RPx>` set the default run page, `<Tx>…` schedules, `<D*>` delete all,
`<ID><nn><E>` assign sign ID (sent raw, without a checksum).

## Sources

The protocol details were pieced together from these excellent resources:

- [Kevin's blog — RPi UART and Maplin N00GA / AM03127 LED display](https://emalliab.wordpress.com/2015/04/27/rpi-uart-and-maplins-n00ga-or-am03127-led-display/)
  (wiring, checksum, pointers to the manual)
- [sixleds](https://github.com/schorschii/sixleds) — GPL-3.0 AM004-03127/03128
  controller library, used as the reference for the packet format, checksum
  algorithm, schedules and extended character table
- [amoled](https://github.com/askarel/amoled) — shell script with a handy
  listing of the effect, wait, bell, colour and font tags
- [N00GA technical manual](https://www.yumpu.com/en/document/view/18868597/n00ga-technical-manualpdf-filesize)
  — the original Maplin/Amplus protocol document
- The `--method` speed/style letter map was worked out empirically on the
  actual N01GA, as it is not fully documented anywhere above.

## License

GPL-3.0 — see [LICENSE](LICENSE).
