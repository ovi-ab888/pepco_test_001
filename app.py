"""
care_label.py
==============
PEPCO Care Label — Pad generator.

One Pad page =
    * N x "Front Part 1"  (one per size: cm_size, |PEPCO|, EAN, SKU, washing
      code pictogram, then the START of the long Composition_Care text)
    * 5 panels that carry the REST of the Composition_Care text, in this
      reading order:
          Front Part 1 (lower part) -> Back Part 1 -> Front Part 2
          -> Back Part 2 -> Front Part 3 -> Back Part 3
      (Composition_Care is one long text with blank lines used as vertical
      gaps; it is wrapped with real Arial metrics and poured line by line
      into the panels, exactly like the sample file.)

Pad template choice (per group of sizes):
      <= 6 sizes -> Care_Label_Pad.pdf     (6 Front Part 1 slots)
      7-8 sizes  -> Care_Label_Pad 2.pdf   (8 Front Part 1 slots)
      > 8 sizes  -> split into several Pad pages (8 per page)
Unused Front Part 1 slots are simply left empty.

Data columns used (from the editable table / CSV):
    cm_size, barcode, SKU, washing_code, Composition_Care      <- label content
    Order_ID, Style, Supplier_product_code, Colour, today_date,
    Designer, Item_classification, Supplier_name               <- Pad header

Repo structure needed:
    labels/care_label.py                       (this file)
    config/care_label_mapping.json
    fonts/ArialRegular.ttf  fonts/ArialBold.ttf
    fonts/PEPCO_Ovi.ttf     fonts/Tahoma.ttf
    templates/Care label/   Front Side_part1.pdf, Front Side.pdf, Back Side.pdf,
                            Care_Label_Pad.pdf, Care_Label_Pad 2.pdf
    (template file names are matched ignoring case, spaces and underscores)
"""

import json
import os

import fitz  # PyMuPDF

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
CONFIG_PATH = os.path.join(BASE_DIR, "config", "care_label_mapping.json")
TEMPLATES_ROOT = os.path.join(BASE_DIR, "templates")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")

BLACK = (0, 0, 0, 1)  # CMYK K100, print-safe black (same as the other labels)

REQUIRED_COLUMNS = ["cm_size", "barcode", "SKU", "washing_code", "Composition_Care"]


class CareLabelOverflow(ValueError):
    """Composition_Care is longer than the 6 text areas can hold."""


# --------------------------------------------------------------------------
# helpers: config, file lookup, fonts
# --------------------------------------------------------------------------
def load_mapping(config_path=CONFIG_PATH):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _norm(name: str) -> str:
    """'Front Side_part1.pdf' -> 'frontsidepart1' (ignore case/space/_/-/extension)."""
    base = os.path.splitext(name)[0]
    return "".join(ch for ch in base.lower() if ch.isalnum())


def _find_templates_dir() -> str:
    """templates/Care label  (also matches 'Care Label', 'Care_Label', ...)."""
    for entry in os.listdir(TEMPLATES_ROOT):
        full = os.path.join(TEMPLATES_ROOT, entry)
        if os.path.isdir(full) and _norm(entry) == "carelabel":
            return full
    raise FileNotFoundError(f"templates/Care label folder not found under {TEMPLATES_ROOT}")


def _find_template(key: str) -> str:
    folder = _find_templates_dir()
    for entry in os.listdir(folder):
        if _norm(entry) == key and entry.lower().endswith(".pdf"):
            return os.path.join(folder, entry)
    raise FileNotFoundError(f"Care Label template '{key}' not found in {folder}")


def _find_font(*candidates) -> str:
    """Case-insensitive lookup of a font file in fonts/."""
    wanted = {_norm(c) for c in candidates}
    for entry in os.listdir(FONTS_DIR):
        if entry.lower().endswith((".ttf", ".otf")) and _norm(entry) in wanted:
            return os.path.join(FONTS_DIR, entry)
    raise FileNotFoundError(f"Font {candidates} not found in {FONTS_DIR}")


class _Fonts:
    """Loads the 3 Care Label fonts once: measuring objects + file paths."""

    def __init__(self):
        self.files = {
            "arial": _find_font("ArialRegular", "arial"),
            "arialb": _find_font("ArialBold", "arialbd"),
            "ovi": _find_font("PEPCO_Ovi"),
        }
        self.objs = {k: fitz.Font(fontfile=v) for k, v in self.files.items()}

    def register(self, page):
        for key, path in self.files.items():
            page.insert_font(fontname=key, fontfile=path)

    def width(self, key, text, size):
        return self.objs[key].text_length(text, fontsize=size)


def _s(value) -> str:
    """Cell -> clean string (NaN / None -> '')."""
    if value is None or (isinstance(value, float) and value != value):
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d-%m-%Y")
    s = str(value)
    return "" if s.strip().lower() == "nan" else s


# --------------------------------------------------------------------------
# text flow
# --------------------------------------------------------------------------
def wrap_composition(text: str, fonts: _Fonts, size: float, width: float,
                     wide_prefixes=(), wide_width: float = None) -> list:
    """
    Wrap Composition_Care into lines. Every '\\n' starts a new line; an empty
    line stays an EMPTY string (= one blank line of vertical gap).
    Paragraphs starting with one of `wide_prefixes` (e.g. "Skupljanje" - the
    shrinkage line, which the sample prints on ONE line) may use the wider
    `wide_width` if that keeps them on a single line.
    """
    lines = []
    text = _s(text).replace("\r\n", "\n").replace("\r", "\n")
    for para in text.split("\n"):
        para = " ".join(para.split())
        if not para:
            lines.append("")
            continue
        if (wide_width and para.startswith(tuple(wide_prefixes))
                and fonts.width("arial", para, size) <= wide_width):
            lines.append(para)
            continue
        cur = ""
        for word in para.split():
            trial = f"{cur} {word}" if cur else word
            if fonts.width("arial", trial, size) <= width:
                cur = trial
                continue
            if cur:
                lines.append(cur)
                cur = ""
            # a single word wider than the box -> hard-break by characters
            while fonts.width("arial", word, size) > width and len(word) > 1:
                cut = len(word) - 1
                while cut > 1 and fonts.width("arial", word[:cut], size) > width:
                    cut -= 1
                lines.append(word[:cut])
                word = word[cut:]
            cur = word
        if cur:
            lines.append(cur)
    return lines


def _capacity(first_baseline: float, last_baseline: float, pitch: float) -> int:
    return int((last_baseline - first_baseline) / pitch + 1e-6) + 1


def flow_into_panels(lines: list, mapping: dict) -> dict:
    """
    Pour `lines` into front1 + the 5 panels in reading order.
    Returns {"front1": [...], "back1": [...], ...}. Blank lines at the TOP of
    a panel are dropped (a gap that lands on a panel edge must not push the
    next text down). Raises CareLabelOverflow if text is left over.
    """
    comp = mapping["composition"]
    pitch, last = comp["line_pitch"], comp["last_baseline"]
    order = [("front1", comp["front1_first_baseline"])] + \
            [(p["name"], p["first_baseline"]) for p in mapping["panels"]]

    out, i = {}, 0
    for name, first in order:
        cap = _capacity(first, last, pitch)
        while i < len(lines) and lines[i] == "":   # trim blank lines at panel top
            i += 1
        chunk = lines[i:i + cap]
        out[name] = chunk
        i += len(chunk)
    rest = [ln for ln in lines[i:] if ln != ""]
    if rest:
        raise CareLabelOverflow(
            f"Composition_Care is too long for the Care Label: {len(rest)}+ line(s) "
            f"do not fit after Back Part 3. Shorten the composition text."
        )
    return out


def _draw_lines(page, fonts, rect, first_baseline, lines, mapping):
    comp = mapping["composition"]
    size, pitch = comp["font_size"], comp["line_pitch"]
    cx = (rect.x0 + rect.x1) / 2
    for n, ln in enumerate(lines):
        if not ln:
            continue
        w = fonts.width("arial", ln, size)
        page.insert_text((cx - w / 2, rect.y0 + first_baseline + n * pitch), ln,
                         fontsize=size, fontname="arial", color=BLACK)


# --------------------------------------------------------------------------
# drawing the pieces
# --------------------------------------------------------------------------
def _draw_front1_fields(page, fonts, rect, row, mapping):
    ff = mapping["front_fields"]
    cx = (rect.x0 + rect.x1) / 2
    a, big, ovi = ff["arial_size"], ff["cm_size_font"], ff["ovi_size"]

    def centered(text, font, size, baseline):
        if not text:
            return
        w = fonts.width(font, text, size)
        page.insert_text((cx - w / 2, rect.y0 + baseline), text, fontsize=size,
                         fontname=font, color=BLACK)

    centered(_s(row.get("cm_size")).strip(), "arialb", big, ff["cm_size_baseline"])
    centered(ff.get("pepco_text", "|PEPCO|"), "arial", a, ff["pepco_baseline"])
    barcode = _s(row.get("barcode")).strip()
    centered(f"EAN: {barcode}" if barcode else "", "arial", a, ff["ean_baseline"])
    sku = _s(row.get("SKU")).strip()
    centered(f"SKU {sku}" if sku else "", "arialb", a, ff["sku_baseline"])
    centered(_s(row.get("washing_code")).strip(), "ovi", ovi, ff["washing_baseline"])


def _fill_pad_header(page, rows, mapping):
    tahoma = None
    try:
        tahoma = _find_font("Tahoma")
        page.insert_font(fontname="tahoma", fontfile=tahoma)
    except FileNotFoundError:
        pass
    fontname = "tahoma" if tahoma else "helv"

    for field in mapping.get("header", []):
        vals = [_s(r.get(field["name"])).strip() for r in rows]
        vals = [v for v in vals if v]
        if not vals:
            continue
        sep = field.get("join_unique")
        value = sep.join(dict.fromkeys(vals)) if sep else vals[0]
        page.insert_text((field["x"], field["y"]), value, fontsize=field["font_size"],
                         fontname=fontname, color=BLACK)


def _show(page, rect, template_path):
    src = fitz.open(template_path)
    page.show_pdf_page(fitz.Rect(rect), src, 0)
    src.close()


# --------------------------------------------------------------------------
# grouping + generation
# --------------------------------------------------------------------------
def group_rows_for_pads(rows: list, mapping: dict = None) -> list:
    """
    Consecutive rows with the same Composition_Care share a Pad (a different
    composition always starts a new Pad), at most 8 sizes (the biggest Pad
    template) per Pad page.
    """
    if mapping is None:
        mapping = load_mapping()
    biggest = max(p["max_units"] for p in mapping["pads"])
    groups, cur, cur_key = [], [], None
    for row in rows:
        key = _s(row.get("Composition_Care")).strip()
        if cur and (key != cur_key or len(cur) >= biggest):
            groups.append(cur)
            cur = []
        cur.append(row)
        cur_key = key
    if cur:
        groups.append(cur)
    return groups


def pick_pad_for_group(n_units: int, mapping: dict) -> dict:
    """Smallest Pad template that has enough Front Part 1 slots."""
    for pad in sorted(mapping["pads"], key=lambda p: p["max_units"]):
        if n_units <= pad["max_units"]:
            return pad
    raise ValueError(f"No Care Label Pad template holds {n_units} sizes")


def generate_pad_for_group(group_rows: list, mapping: dict = None, fonts: _Fonts = None) -> bytes:
    """ONE Pad page (PDF bytes) for a group of rows (one row = one size)."""
    if mapping is None:
        mapping = load_mapping()
    if not group_rows:
        raise ValueError("group_rows is empty")
    fonts = fonts or _Fonts()

    pad_cfg = pick_pad_for_group(len(group_rows), mapping)
    comp = mapping["composition"]
    lines = wrap_composition(group_rows[0].get("Composition_Care", ""), fonts,
                             comp["font_size"], comp["wrap_width"],
                             comp.get("wide_prefixes", ()), comp.get("wide_width"))
    flow = flow_into_panels(lines, mapping)   # may raise CareLabelOverflow

    pad_doc = fitz.open(_find_template(pad_cfg["template"]))
    page = pad_doc[0]
    fonts.register(page)
    _fill_pad_header(page, group_rows, mapping)

    front1_tpl = _find_template(mapping["front1_template"])
    for rect_coords, row in zip(pad_cfg["front_rects"], group_rows):
        rect = fitz.Rect(rect_coords)
        _show(page, rect, front1_tpl)
        _draw_front1_fields(page, fonts, rect, row, mapping)
        _draw_lines(page, fonts, rect, comp["front1_first_baseline"], flow["front1"], mapping)
    # Front Part 1 slots with no size stay as the empty template box

    for panel in mapping["panels"]:
        rect = fitz.Rect(panel["rect"])
        _show(page, rect, _find_template(panel["template"]))
        _draw_lines(page, fonts, rect, panel["first_baseline"], flow[panel["name"]], mapping)

    data = pad_doc.tobytes()
    pad_doc.close()
    return data


def generate_batch(rows: list, config_path=CONFIG_PATH) -> list:
    """List of Pad PDF bytes, one per group."""
    mapping = load_mapping(config_path)
    fonts = _Fonts()
    return [generate_pad_for_group(g, mapping, fonts) for g in group_rows_for_pads(rows, mapping)]


def generate_batch_pdf(rows: list, config_path=CONFIG_PATH) -> bytes:
    """Same as generate_batch(), merged into ONE multi-page PDF."""
    out = fitz.open()
    for pad_bytes in generate_batch(rows, config_path):
        src = fitz.open("pdf", pad_bytes)
        out.insert_pdf(src)
        src.close()
    data = out.tobytes()
    out.close()
    return data


def missing_columns(rows: list) -> list:
    """Care Label columns that are absent or completely empty in the table."""
    return [c for c in REQUIRED_COLUMNS if not any(_s(r.get(c)).strip() for r in rows)]
