"""Split a free-text phone/WhatsApp note into the Contacts tab's Phone and WhatsApp columns (digits only, with the
country code, one number per line) plus the notes that were attached to the numbers.

    split_numbers("Phone: +51 1 514 3300 / WA: +51 943 667 077 (WA name: Van)", "51")
    -> (["5115143300"], ["51943667077"], ["51943667077 WA name: Van"])

Labels: "WA:" -> WhatsApp; "Phone/WA:" (confirmed on both) -> both; "Phone/WA?:" (not confirmed) and "Phone:" -> Phone.
A label applies to the following numbers until the next label, except that a carried-over "WA" label never moves a
landline (a number that does not match the country's mobile_pattern) into WhatsApp; a landline goes to WhatsApp only
when "WA:" is written directly in front of it. Unlabelled numbers go to `default` ("phone" or "wa").
National numbers are converted with the country's phone_prefix: a leading trunk prefix (the country's trunk_prefix, usually 0) is dropped, "(511)"-style area codes
that already start with the prefix are kept, and a short number after a landline inherits that landline's area code."""
import re

_LABEL = re.compile(r"(?i)\b(phone\s*/\s*wa\s*\?|phone\s*/\s*wa|central\s+wa|wa|phone|calls|tel)\s*:?")
_NOTE_LABEL = re.compile(r"(?i)^\s*([A-Za-zÁ-úñ ]{3,30}):\s*")
_NUM = re.compile(r"(?:\+\d{1,3}\s?)?(?:\(\d{2,4}\)\s?)?\d[\d \-]{4,}\d")
_EXT = re.compile(r"(?i)\(?\bext\.?\s*[\d\-]+\)?")
_DROP_NOTES = re.compile(r"(?i)^personal wa( accounts?)?$")


def _mode(label):
    l = re.sub(r"\s+", "", label.lower())
    if l == "phone/wa?":
        return "phone"
    if l == "phone/wa":
        return "both"
    if l in ("wa", "centralwa"):
        return "wa"
    return "phone"


def _normalise(num, prefix, last, trunk="0"):
    digits = re.sub(r"\D", "", num)
    s = num.strip()
    if s.startswith("+"):
        return digits
    m = re.match(r"\((\d{2,4})\)\s*(.*)", s)
    if m:
        area, rest = m.group(1), re.sub(r"\D", "", m.group(2))
        if area.startswith(prefix) and len(area) > len(prefix):
            return area + rest
        return prefix + (area[len(trunk):] if trunk and area.startswith(trunk) else area) + rest
    if trunk and digits.startswith(trunk):
        return prefix + digits[len(trunk):]
    if len(digits) <= 7 and last and len(last) - len(digits) > len(prefix):
        return prefix + last[len(prefix):len(last) - len(digits)] + digits  # same area code as the previous landline
    return prefix + digits


def split_numbers(text, prefix, default="phone", mobile_pattern=None, trunk="0"):
    phones, was, notes = [], [], []
    if not text:
        return phones, was, notes
    text = str(text)
    ext = [(m.start(), m.group(0).strip("() ")) for m in _EXT.finditer(text)]
    text = _EXT.sub(lambda m: " " * len(m.group(0)), text)
    # walk the text: labels switch the mode, numbers are collected, parenthesised text is a note on the last number
    tokens = sorted([(m.start(), "label", m.group(1)) for m in _LABEL.finditer(text)] +
                    [(m.start(), "num", m.group(0)) for m in _NUM.finditer(text)] +
                    [(m.start(), "note", m.group(1)) for m in re.finditer(r"\(([^()]*[A-Za-zÁ-ú][^()]*)\)", text)] +
                    [(p, "note", e) for p, e in ext])
    # drop label/note hits that sit inside a number match or inside a note
    spans = [(m.start(), m.end()) for m in _NUM.finditer(text)] + [(m.start(), m.end()) for m in re.finditer(r"\([^()]*\)", text)]
    mobile = re.compile(mobile_pattern) if mobile_pattern else None
    mode, last, current, fresh = default, None, None, False
    pending = []  # free-text department labels such as "Ventas:" that precede a number
    for pos, kind, val in tokens:
        if kind == "label":
            if any(a < pos < b for a, b in spans):
                continue
            mode, fresh = _mode(val), True
        elif kind == "num":
            if any(a < pos < b for a, b in spans if (a, b) not in [(m.start(), m.end()) for m in _NUM.finditer(text)]):
                continue
            n = _normalise(val, prefix, last, trunk)
            last = current = n
            use = mode
            if mode == "wa" and not fresh and mobile and not mobile.fullmatch(n[len(prefix):]):
                use = "phone"  # carried-over WA label, but this is a landline
            fresh = False
            if use in ("phone", "both") and n not in phones:
                phones.append(n)
            if use in ("wa", "both") and n not in was:
                was.append(n)
            before = text[max(0, pos - 40):pos]
            lab = re.search(r"([A-Za-zÁ-úñ][A-Za-zÁ-úñ ]{2,28}):\s*$", before)
            if lab and not _LABEL.fullmatch(lab.group(1).strip() + ":") and lab.group(1).strip().lower() not in ("wa", "phone", "phone/wa", "tel", "calls", "central wa"):
                notes.append(f"{n} {lab.group(1).strip()}")
        else:
            v = val.strip()
            if current and v and not _DROP_NOTES.match(v):
                notes.append(f"{current} {v}")
    return phones, was, notes


def to_columns(text, prefix, default="phone", mobile_pattern=None, trunk="0"):
    """-> (Phone cell, WhatsApp cell, notes list). Cells hold one number per line, or None when empty."""
    p, w, notes = split_numbers(text, prefix, default, mobile_pattern, trunk)
    return ("\n".join(p) or None), ("\n".join(w) or None), notes
