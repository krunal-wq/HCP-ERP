"""
icon_upgrade.py — replace emoji icons with Bootstrap Icons (premium UI pass).

Phased, file-by-file. For each file:
  1. Recover any double-mojibake'd emoji (utf8->cp1252->utf8) back to real emoji.
  2. Strip redundant emoji that sit inside <span class="nav-txt"> (those rows
     already carry a proper <i class="bi ..."> in their .nav-ic span).
  3. Replace remaining *label* emoji (right after an HTML '>') with a mapped
     <i class="bi ..."> icon. CSS / JS / attribute strings are left untouched.

Plain arrows (←  →) are intentionally left alone (typographic, not icons).

Run:  python scripts/fixes/icon_upgrade.py <file1> [file2 ...]
Prints a per-file report; writes changes in place.
"""
import re
import sys
from collections import Counter

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# ── emoji -> Bootstrap Icon (1.11.3) name ─────────────────────────────────
EMOJI_BI = {
    '📊': 'bi-graph-up',          '📈': 'bi-graph-up-arrow',
    '📉': 'bi-graph-down-arrow',  '📋': 'bi-clipboard-data',
    '📄': 'bi-file-earmark-text', '🧾': 'bi-receipt',
    '📁': 'bi-folder',            '📦': 'bi-box-seam',
    '👥': 'bi-people',            '👤': 'bi-person',
    '🏆': 'bi-trophy',            '🔬': 'bi-eyedropper',
    '🧪': 'bi-droplet-half',      '⚗': 'bi-droplet-half',
    '⚙': 'bi-gear',               '🛠': 'bi-tools',
    '👔': 'bi-person-badge',      '🪪': 'bi-person-vcard',
    '🤝': 'bi-people',            '🔑': 'bi-key',
    '🏠': 'bi-house-door',        '🛒': 'bi-cart',
    '🛍': 'bi-bag',               '🧴': 'bi-droplet',
    '📧': 'bi-envelope',          '✉': 'bi-envelope',
    '🔍': 'bi-search',            '📅': 'bi-calendar-event',
    '📆': 'bi-calendar-event',    '⏰': 'bi-alarm',
    '✏': 'bi-pencil',             '📝': 'bi-pencil-square',
    '🗑': 'bi-trash',             '⭐': 'bi-star-fill',
    '🌟': 'bi-star-fill',         '🟡': 'bi-circle-fill',
    '🟢': 'bi-circle-fill',       '🔴': 'bi-circle-fill',
    '🚀': 'bi-rocket-takeoff',    '💰': 'bi-cash-coin',
    '💵': 'bi-cash',              '✅': 'bi-check-circle',
    '✔': 'bi-check-circle',       '❌': 'bi-x-circle',
    '✖': 'bi-x-circle',           '⚠': 'bi-exclamation-triangle',
    '🔔': 'bi-bell',              '📌': 'bi-pin-angle',
    '🔒': 'bi-lock',              '🔓': 'bi-unlock',
    '🏭': 'bi-building',          '🧰': 'bi-toolbox',
    '📞': 'bi-telephone',         '🌐': 'bi-globe',
    '🔗': 'bi-link-45deg',        '📍': 'bi-geo-alt',
    '🏷': 'bi-tags',              '🧮': 'bi-calculator',
    '🗂': 'bi-folder2-open',      '📚': 'bi-journals',
    '🔖': 'bi-bookmark',          '💡': 'bi-lightbulb',
    '🎯': 'bi-bullseye',          '🏢': 'bi-building',
    '📥': 'bi-box-arrow-in-down', '📤': 'bi-box-arrow-up',
    '🧹': 'bi-eraser',            '🔧': 'bi-wrench',
    '✕': 'bi-x-lg',               '✗': 'bi-x-lg',
    '✘': 'bi-x-lg',               '➕': 'bi-plus-lg',
    '🎉': 'bi-stars',             '🎊': 'bi-stars',
    '💤': 'bi-moon-stars',        '🎂': 'bi-gift',
    '🎖': 'bi-award',             '🏅': 'bi-award',
    '🙏': 'bi-heart',             '🕐': 'bi-clock',
    '⏳': 'bi-hourglass-split',    '💎': 'bi-gem',
    '🔥': 'bi-fire',              '⏱': 'bi-stopwatch',
    '🗓': 'bi-calendar3',         '🔄': 'bi-arrow-repeat',
    '🔁': 'bi-arrow-repeat',      '⛔': 'bi-slash-circle',
    '🚫': 'bi-slash-circle',      '💬': 'bi-chat-dots',
    '🗨': 'bi-chat',              'ℹ': 'bi-info-circle',
    '✨': 'bi-stars',             '🟠': 'bi-circle-fill',
    '🟣': 'bi-circle-fill',       '🔵': 'bi-circle-fill',
    '⬆': 'bi-arrow-up',          '⬇': 'bi-arrow-down',
    '➖': 'bi-dash-lg',           '❗': 'bi-exclamation-lg',
    '❓': 'bi-question-lg',        '📈': 'bi-graph-up-arrow',
    '🎓': 'bi-mortarboard',       '🏦': 'bi-bank',
    '💳': 'bi-credit-card',       '📃': 'bi-file-text',
    '🖨': 'bi-printer',           '📲': 'bi-phone',
    '💼': 'bi-briefcase',         '🗒': 'bi-journal-text',
}
DEFAULT_BI = 'bi-dot'

VS = '️'   # emoji variation selector


def _is_emoji(ch):
    o = ord(ch)
    return (0x1F000 <= o <= 0x1FAFF or 0x2600 <= o <= 0x27BF or
            0x2B00 <= o <= 0x2BFF or 0x2300 <= o <= 0x23FF or o == 0xFE0F)


# one pictographic emoji (NOT plain arrows), optional variation selector
EMOJI_ONE = re.compile(
    r'(?:[\U0001F000-\U0001FAFF☀-➿⬀-⯿⌀-⏿])️?')


def recover_mojibake(text):
    """utf8->cp1252->utf8 double-encoded emoji back into real emoji.
    Only rewrites a non-ASCII run if it cleanly recovers to all-emoji."""
    def repl(m):
        run = m.group(0)
        try:
            rec = run.encode('cp1252').decode('utf-8')
        except Exception:
            return run
        if rec and all(_is_emoji(c) or c == VS for c in rec):
            return rec
        return run
    return re.sub(r'[^\x00-\x7F]+', repl, text)


def strip_navtxt_emoji(text):
    """Remove leading emoji inside <span class="nav-txt"> (icon already in nav-ic)."""
    pat = re.compile(r'(<span class="nav-txt">)((?:' + EMOJI_ONE.pattern + r'|\s)+)')
    return pat.sub(lambda m: m.group(1), text)


# tags whose text content cannot hold an <i> element — strip emoji instead
SKIP_TAGS = {'option', 'title', 'textarea'}


def label_emoji_to_bi(text):
    """Replace an emoji that is the first content of an element with the mapped
    <i class='bi ...'> icon. For text-only tags (option/title/textarea) the emoji
    is stripped. Emoji inside JS/CSS/attribute strings are left untouched
    (they don't sit right after an element's opening tag)."""
    report = []
    pat = re.compile(r'(<(\w+)(?:\s[^>]*)?>)\s*(' + EMOJI_ONE.pattern + r')\s*')

    def repl(m):
        tag = m.group(2).lower()
        ch = m.group(3).rstrip(VS)
        if tag in SKIP_TAGS:
            report.append((ch, f'(stripped:{tag})'))
            return m.group(1)
        bi = EMOJI_BI.get(ch, DEFAULT_BI)
        report.append((ch, bi))
        return f'{m.group(1)}<i class="bi {bi}"></i> '
    return pat.sub(repl, text), report


def process(path):
    src = open(path, encoding='utf-8').read()
    recovered = recover_mojibake(src)
    before = len(EMOJI_ONE.findall(recovered))

    txt = strip_navtxt_emoji(recovered)
    txt, rep = label_emoji_to_bi(txt)
    after = len(EMOJI_ONE.findall(txt))

    if txt != src:
        open(path, 'w', encoding='utf-8').write(txt)
    print(f'\n=== {path} ===')
    print(f'  pictographic emoji  before: {before}  ->  after: {after}')
    stripped = before - after - len(rep)
    if stripped:
        print(f'    stripped from nav-txt (redundant): {stripped}')
    for (ch, bi), n in Counter(rep).most_common():
        flag = '  <-- UNMAPPED' if bi == DEFAULT_BI else ''
        print(f'    label  {ch!r} -> <i class="bi {bi}"> x{n}{flag}')
    # show what is left (JS/CSS/attr strings we intentionally skipped)
    leftover = []
    for m in EMOJI_ONE.finditer(txt):
        i = m.start()
        leftover.append((m.group(0), txt[max(0, i - 24):i].split(chr(10))[-1][-22:]))
    if leftover:
        print(f'  remaining ({len(leftover)}) — skipped (not element text):')
        for ch, ctx in leftover[:40]:
            print(f'    {ch!r:6} ...{ctx!r}')


if __name__ == '__main__':
    for p in sys.argv[1:]:
        process(p)
