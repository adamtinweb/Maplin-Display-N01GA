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

**Power-loss quirk:** the sign forgets its ID whenever it loses power, and
then silently ignores every command except the broadcast ID assignment.
`LedSign.send()` self-heals: on a missing ACK it re-broadcasts the ID and
retries once, so all the scripts here recover automatically after a power
cycle — no manual `--set-id` needed.

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

**Display method** (`--method`) — first decoded by experiment on the N01GA,
later confirmed exactly by the official AM004-03127 manual. The four letter
groups select the effect speed and the position within the group selects the
style:

| Group | Speed |
|---|---|
| `A`–`E` | level 1, fastest |
| `Q`–`U` | level 2, middle fast |
| `a`–`e` | level 3, middle slow |
| `q`–`u` | level 4, slowest |

Within each group: 1st letter (`A`/`Q`/`a`/`q`) = normal, 2nd = blinking,
3rd–5th = built-in songs 1–3 (the sign beeps a tune while the text holds).
The default is `q` — normal style, slowest speed, no beeps.

**Inline codes** usable inside a message: `<KT>` live time, `<KD>` live date,
`<AA>`–`<AE>` font size/style. Common symbols such as `£ € ° © ½ →` are
translated automatically to the sign's extended character set (`<Uxx>` codes).

## Ticker (`ticker.py`)

A ready-made FTSE-style ticker that scrolls live market prices and news on
the sign:

```
python ticker.py --port COM11                # run forever, refresh every 5 min
python ticker.py --port COM11 --interval 60  # refresh every minute
python ticker.py --port COM11 --once         # single update
python ticker.py --dry-run --once            # preview the text, no sign needed
```

Out of the box it shows Expedia (EXPE), Bitcoin in GBP, and three LSE ETFs —
iShares Core FTSE 100 (ISF), Vanguard S&P 500 Acc (VUAG) and Xtrackers
Nasdaq 100 (XNAQ) — each with an up/down arrow and percent change against the
previous close, followed by the current top BBC News headline. Quotes come
from Yahoo Finance's public chart API (no API key required) and the headline
from the BBC News RSS feed. Edit the `QUOTES` list at the top of the script
to change the instruments.

## Effects demo (`demo.py`)

A guided tour of every display effect, each paired with a fitting famous
quote, plus a variety of lagging effects and hold times along the way. The
full running order:

| # | Effect | Shown with |
|---|---|---|
| 1 | `A` appear instantly | "Carpe diem" — Horace |
| 2 | `B` X-open from centre | "To be, or not to be" — Shakespeare |
| 3 | `C` curtain up | "All the world's a stage" — Shakespeare |
| 4 | `D` curtain down | "Good night, sweet prince" — Shakespeare |
| 5 | `E` scroll left (classic ticker) | "The only thing we have to fear is fear itself" — Roosevelt |
| 6 | `F` scroll right | "Float like a butterfly, sting like a bee" — Muhammad Ali |
| 7 | `G` V-open | "Eureka!" — Archimedes |
| 8 | `H` V-close | "I'll be back" — The Terminator |
| 9 | `I` scroll up | "One small step for man, one giant leap for mankind" — Armstrong |
| 10 | `J` scroll down | "What goes up must come down" — Newton |
| 11 | `K` hold (10 s) | "Stay hungry, stay foolish" — Steve Jobs |
| 12 | `L` snow | "Let it snow" — Sammy Cahn |
| 13 | `M` twinkle | "Twinkle, twinkle, little star" — Jane Taylor |
| 14 | `N` block move | "Rome wasn't built in a day" |
| 15 | `P` random pixels | "God does not play dice" — Einstein |
| 16 | `Q` pen-writing demo | the sign hand-writes "hello world" |
| 17 | `R` pen-writing demo | the sign hand-writes "welcome" |
| 18 | `S` pen-writing demo | the sign hand-writes "Amplus" |

```
python demo.py --port COM11           # play the tour once (about 4 minutes)
python demo.py --port COM11 --loop    # repeat forever
python demo.py --port COM11 --fast    # quicker scroll speed, shorter pauses
```

Static effects use short quotes (the display fits ~13 characters without
scrolling); the four scrolling effects carry full-length quotes.

## Train departure board (`trains.py`)

A live next-train board that vertical-scrolls between routes, holding each
page for 5 seconds and refreshing the data every minute:

- **`HRO→LST 08:14`** — the next Elizabeth line train from Harold Wood
  towards London Liverpool Street, from the
  [TfL Unified API](https://api.tfl.gov.uk/) (no API key needed).
  Shenfield/Brentwood-bound trains and the short Gidea Park/Romford
  terminators are filtered out, since they never reach Liverpool Street.
- **`LOO→LSK 09:04`** — the next Looe Valley Line train from Looe to
  Liskeard, live National Rail Darwin data via the public
  [Huxley2](https://huxley2.azurewebsites.net/) proxy. Late-running trains
  show their revised time, or `DLYD`/`CANX` when Darwin reports them
  delayed or cancelled; `NONE` means no trains (the branch sleeps
  overnight).

```
python trains.py --port COM11               # run forever, refresh every minute
python trains.py --port COM11 --once        # single update
python trains.py --dry-run --once           # preview the pages, no sign needed
python trains.py --port COM11 --invert      # dark text on a lit background
python trains.py --port COM11 --flip        # rotated 180° for upside-down mounting
```

Routes use National Rail CRS codes with the sign's arrow glyph, sized to
the display's ~13 character width. To add or change routes, edit the
`SERVICES` list — each entry is a route label plus a function returning the
next departure time; the sign cycles up to six pages.

`--invert` uses the AM03127 `<CL>` "Inversed Red" colour code. `--flip` is
for hanging the sign upside down: the protocol has no rotate command, so at
startup the script uploads a 180°-rotated 5×7 font (A–Z, 0–9, punctuation)
into the sign's 64 redefinable character slots via the `<Fsxy>` command
(takes ~10 s), then sends each message reversed and mapped to those glyphs,
and swaps the scroll direction so the motion reads correctly. The two
switches can be combined. The font machinery lives in `led_sign.py`
(`install_flipped_font()` / `flip_text()`) for use by other scripts; note
live inline codes like `<KT>` cannot be flipped, as the sign renders them
itself.

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
`<ID><nn><E>` assign sign ID (sent raw, without a checksum; this is the
only command an ID-less sign responds to — see the power-loss quirk above).

Inside a message the protocol also supports `<Cx>` colour codes (on the
red-only N01GA, `<CL>` "Inversed Red" gives inverse video), `<Bx>` bell
beeps of configurable duration, `<Nxx>` column positioning, and `<Fsxy>` +
8 bytes to redefine the glyphs of European character slots `<U40>`–`<U7F>`
(`<DU>` restores the factory table) — the trick behind `--flip`.

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
- [AM004-03128/03127 LED Display Board Communication v2.2 (PDF)](https://asset.conrad.com/media10/add/160267/c1/-/en/000590998DS01/datasheet-590998-mc-crypt-am03127-h11.pdf)
  — the official Amplus protocol datasheet: authoritative source for the
  display-method speed table, colour codes, column positioning and the
  `<Fsxy>` font-redefinition command used by `--flip`
- The `--method` letter map was first worked out empirically on the actual
  N01GA, then confirmed against the datasheet above. The power-loss ID
  quirk is empirical.

## License

GPL-3.0 — see [LICENSE](LICENSE).
