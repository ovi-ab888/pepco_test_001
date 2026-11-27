"""
care_label.py  (AW27)
=====================
PEPCO Care Label - Pad generator, AW27 design (30 x 60 mm panels).

One Pad page =
    Row 1 :  N x "Front side 1"  (one per size: cm_size, |PEPCO|, EAN, SKU,
             washing pictogram + the FIXED red "KEEP AWAY FROM FIRE" text that
             is already printed in the template)   +   ONE "Back side 1"
             (fixed red fire text continues in the template, then the
             Composition_Care text STARTS here)
    Row 2.. :  Front side 2, Back side 2, Front side 3, Back side 3, ...
               (Composition_Care is poured line by line into these panels)

How many panels are used depends only on the length of Composition_Care.
Front panels carry a small panel number (1, 2, 3 ...) top-right.
Back panels carry no number.

Text rules
    * Composition_Care is wrapped with real Arial metrics (centered lines).
    * An empty line in the text = small vertical gap (blank_height pt),
      NOT a full line. Blank lines at the top of a panel are dropped.
    * "Skupljanje: ..." line is pinned to the BOTTOM of the panel where the
      care text ends (needs room for a gap above it, else next panel's bottom).
      "Made in Bangladesh ... Produced by ... addresses" then starts after
      skupljanje_gap_lines (5) blank lines, i.e. at the top of the next panel,
      and simply flows on (it may be split over several panels).
    * The "@ customer@pepco.eu" artwork is always placed in the LAST panel,
      its bottom edge 10 mm above the panel bottom. If the last text line would
      touch it, it goes to a new panel.
    * Back panels stop 5 mm above the pink dash line.

Pad template choice (per group of sizes with identical Composition_Care):
      1-5 sizes -> Care_Label_Pad_1.pdf    (5 Front side 1 + Back side 1)
      6 sizes   -> Care_Label_Pad_2_1.pdf  (6 Front side 1 + Back side 1)
      7 sizes   -> Care_Label_Pad_3.pdf    (7 Front side 1 + Back side 1)
      > 7 sizes -> split into several Pad pages
Back side 1 always sits right after the last size (4 sizes -> Back side 1 in
column 5, column 6 stays empty).

Data columns used (from the editable table / CSV):
    cm_size, barcode, SKU, washing_code, Composition_Care     <- label content
    Order_ID, Style, Supplier_product_code, Colour, today_date,
    Designer, Item_classification, Supplier_name              <- Pad header

Repo structure needed:
    labels/care_label.py                       (this file)
    config/care_label_mapping.json
    fonts/ArialRegular.ttf  fonts/ArialBold.ttf
    fonts/PEPCO_Ovi.ttf     fonts/Tahoma.ttf
    templates/Care label/   1st_label_front_side.pdf, 1st_label_Back_side.pdf,
                            Front_Side_1.pdf, Back_Side_1.pdf,
                            Care_Label_Pad_1.pdf, Care_Label_Pad_2_1.pdf,
                            Care_Label_Pad_3.pdf, customer_pepco_eu.pdf
    (template file names are matched ignoring case, spaces and underscores)
"""

import json
import os
import re

import fitz  # PyMuPDF

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
CONFIG_PATH = os.path.join(BASE_DIR, "config", "care_label_mapping.json")
TEMPLATES_ROOT = os.path.join(BASE_DIR, "templates")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")

BLACK = (0, 0, 0, 1)  # CMYK K100, print-safe black (same as the other labels)

REQUIRED_COLUMNS = ["cm_size", "barcode", "SKU", "washing_code", "Composition_Care"]

_EPS = 0.05  # tolerance when comparing baselines (pt)


class CareLabelOverflow(ValueError):
    """Composition_Care is longer than the Pad can hold."""


# --------------------------------------------------------------------------
# helpers: config, file lookup, fonts
# --------------------------------------------------------------------------
def load_mapping(config_path=CONFIG_PATH):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _norm(name: str) -> str:
    """'Front_Side_1.pdf' -> 'frontside1' (ignore case/space/_/-/extension)."""
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
# text wrapping
# --------------------------------------------------------------------------
def wrap_composition(text: str, fonts: _Fonts, size: float, width: float,
                     wide_prefixes=(), wide_width: float = None) -> list:
    """
    Wrap text into lines. Every '\\n' starts a new line; an empty line stays an
    EMPTY string (= one small vertical gap). Paragraphs starting with one of
    `wide_prefixes` (e.g. "Skupljanje") may use the wider `wide_width` if that
    keeps them on a single line.
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


def _trim_blank(lines: list) -> list:
    i, j = 0, len(lines)
    while i < j and lines[i] == "":
        i += 1
    while j > i and lines[j - 1] == "":
        j -= 1
    return lines[i:j]


def split_line_out(text: str, marker: str):
    """
    Cut the line that starts with `marker` ("Skupljanje: ...") out of `text`.
    Returns (text_without_that_line, that_line). No marker/match -> (text, "").
    """
    if not marker:
        return text, ""
    m = re.search(r"(?m)^[ \t]*" + re.escape(marker) + r"[^\n]*\n?", text)
    if not m:
        return text, ""
    return text[:m.start()] + text[m.end():], m.group(0).strip()


def split_composition(text: str, comp: dict):
    """
    Split Composition_Care into (care_text, skupljanje_line, tail_text).
    tail_text starts at the first line beginning with `made_in_marker`
    ("Made in Bangladesh...") and runs to the end (Produced by + addresses).
    skupljanje_line is cut out of the text before that point.
    No Made-in marker -> (text, "", "") and Skupljanje (if any) stays in the flow.
    """
    text = _s(text).replace("\r\n", "\n").replace("\r", "\n")
    marker = comp.get("made_in_marker", "")
    if not marker:
        return text, "", ""
    m = re.search(r"(?m)^[ \t]*" + re.escape(marker), text)
    if not m:
        return text, "", ""
    head, tail = text[:m.start()], text[m.start():]
    head, skup = split_line_out(head, comp.get("skupljanje_marker", ""))
    return head, skup, tail


# --------------------------------------------------------------------------
# panels of one Pad
# --------------------------------------------------------------------------
def build_text_panels(pad_cfg: dict, mapping: dict, n_units: int) -> list:
    """
    The text panels of a Pad in reading order:
        Back side 1, Front side 2, Back side 2, Front side 3, ...
    Each: {name, kind('front'|'back'), number, rect, first_baseline, last_baseline}
    Back side 1 sits DIRECTLY AFTER the last used Front side 1 slot (column n_units),
    e.g. 4 sizes -> columns 1-4 = Front side 1, column 5 = Back side 1, column 6 stays
    empty. Rows 2.. are full rows (Front side 2, Back side 2, ...).
    """
    comp = mapping["composition"]
    pw, ph = mapping["panel_size"]
    ox, oy = pad_cfg["origin"]
    px, py = pad_cfg["pitch"]
    cols, rows = pad_cfg["columns"], pad_cfg["rows"]

    cells = [(0, min(n_units, cols - 1))]         # Back side 1 right after the last size
    for r in range(1, rows):
        for c in range(cols):
            cells.append((r, c))

    panels = []
    for k, (r, c) in enumerate(cells):
        rect = [ox + c * px, oy + r * py, ox + c * px + pw, oy + r * py + ph]
        if k % 2 == 0:                            # back panels: k = 0, 2, 4 ...
            n = k // 2 + 1
            panels.append({
                "name": f"back{n}", "kind": "back", "number": n, "rect": rect,
                "first_baseline": comp["back1_first_baseline"] if n == 1 else comp["back_first_baseline"],
                "last_baseline": comp["back_last_baseline"],
            })
        else:                                     # front panels: k = 1, 3, 5 ...
            n = (k + 1) // 2 + 1
            panels.append({
                "name": f"front{n}", "kind": "front", "number": n, "rect": rect,
                "first_baseline": comp["front_first_baseline"],
                "last_baseline": comp["front_last_baseline"],
            })
    return panels


def front1_rects(pad_cfg: dict, mapping: dict) -> list:
    """Rects of the Front side 1 slots (row 1, left to right)."""
    pw, ph = mapping["panel_size"]
    ox, oy = pad_cfg["origin"]
    px, _ = pad_cfg["pitch"]
    return [[ox + c * px, oy, ox + c * px + pw, oy + ph] for c in range(pad_cfg["max_units"])]


# --------------------------------------------------------------------------
# text flow (height based)
# --------------------------------------------------------------------------
class _Pour:
    """Pours text lines into the panels one after another, tracking baselines."""

    def __init__(self, panels, comp):
        self.panels = panels
        self.pitch = comp["line_pitch"]
        self.blank = comp.get("blank_height", comp["line_pitch"])
        self.idx = 0
        self.y = None           # baseline of the last line in the current panel
        self.pend = 0.0         # pending blank height before the next line
        self.out = {p["name"]: [] for p in panels}
        self.last_used = -1     # index of the last panel that holds text

    def _next_panel(self):
        if self.idx + 1 >= len(self.panels):
            raise CareLabelOverflow(
                "Composition_Care text is too long for this Pad "
                f"(all {len(self.panels)} text panels are full). Shorten the composition text."
            )
        self.idx += 1
        self.y = None
        self.pend = 0.0

    def put(self, text):
        if text == "":
            self.pend += self.blank
            return
        p = self.panels[self.idx]
        y = p["first_baseline"] if self.y is None else self.y + self.pitch + self.pend
        while y > p["last_baseline"] + _EPS:
            self._next_panel()
            p = self.panels[self.idx]
            y = p["first_baseline"]
        self.out[p["name"]].append((y, text))
        self.y, self.pend, self.last_used = y, 0.0, self.idx

    def pin_bottom(self, text, gap_lines=0):
        """Put `text` on the last allowed baseline of the current panel (next panel
        if there is no room for a gap above it); then leave `gap_lines` blank lines."""
        p = self.panels[self.idx]
        if self.y is not None and self.y + self.pitch + self.blank > p["last_baseline"] + _EPS:
            self._next_panel()
            p = self.panels[self.idx]
        y = p["last_baseline"]
        self.out[p["name"]].append((y, text))
        self.y, self.last_used = y, self.idx
        self.pend = gap_lines * self.pitch

    def last_baseline_used(self):
        if self.last_used < 0:
            return None
        lst = self.out[self.panels[self.last_used]["name"]]
        return max(y for y, _ in lst) if lst else None


def flow_into_panels(care_lines, skup_lines, tail_lines, mapping, panels):
    """
    Returns (flow, last_idx): flow = {panel_name: [(baseline, text), ...]},
    last_idx = index (in `panels`) of the LAST panel that is needed
    (it also has room at the bottom for the @ customer@pepco.eu artwork).
    """
    comp = mapping["composition"]
    pour = _Pour(panels, comp)

    for ln in _trim_blank(care_lines):
        pour.put(ln)

    skup = _trim_blank(skup_lines)
    tail = _trim_blank(tail_lines)
    if skup and tail:
        for ln in skup:
            pour.pin_bottom(ln, gap_lines=comp.get("skupljanje_gap_lines", 5))
        for ln in tail:
            pour.put(ln)
    else:
        # no Made-in block (or no Skupljanje line): everything just flows
        for ln in skup:
            pour.put("")
            pour.put(ln)
        if tail:
            pour.put("")
            for ln in tail:
                pour.put(ln)

    last_idx = max(pour.last_used, 0)
    # the e-mail artwork sits at the bottom of the last panel: text must stay above it
    ymax = pour.last_baseline_used()
    if ymax is not None and ymax > mapping["email"]["text_clear_baseline"] + _EPS:
        if last_idx + 1 >= len(panels):
            raise CareLabelOverflow("No panel left for the customer@pepco.eu artwork. Shorten the composition text.")
        last_idx += 1
    return pour.out, last_idx


# --------------------------------------------------------------------------
# drawing the pieces
# --------------------------------------------------------------------------
def _draw_lines(page, fonts, rect, lines, mapping):
    size = mapping["composition"]["font_size"]
    cx = (rect.x0 + rect.x1) / 2
    for y, ln in lines:
        w = fonts.width("arial", ln, size)
        page.insert_text((cx - w / 2, rect.y0 + y), ln, fontsize=size,
                         fontname="arial", color=BLACK)


def _draw_number(page, fonts, rect, n, mapping):
    cfg = mapping["number"]
    txt = str(n)
    w = fonts.width("arial", txt, cfg["font_size"])
    page.insert_text((rect.x0 + cfg["right_edge"] - w, rect.y0 + cfg["baseline"]), txt,
                     fontsize=cfg["font_size"], fontname="arial", color=BLACK)


def _draw_caption(page, fonts, rect, text, mapping):
    cfg = mapping["caption"]
    w = fonts.width("arial", text, cfg["font_size"])
    page.insert_text(((rect.x0 + rect.x1) / 2 - w / 2, rect.y0 - cfg["offset_above"]), text,
                     fontsize=cfg["font_size"], fontname="arial", color=tuple(cfg["color"]))


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

    # size + "cm": drawn as two pieces with a small gap (a normal space is too wide)
    size_txt = _s(row.get("cm_size")).strip()
    m = re.match(r"^(.*?\d)\s*([A-Za-z]+)$", size_txt)
    if m:
        num, unit = m.group(1), m.group(2)
        gap = ff.get("cm_gap", 0.5)
        w1, w2 = fonts.width("arialb", num, big), fonts.width("arialb", unit, big)
        x0 = cx - (w1 + gap + w2) / 2
        page.insert_text((x0, rect.y0 + ff["cm_size_baseline"]), num, fontsize=big, fontname="arialb", color=BLACK)
        page.insert_text((x0 + w1 + gap, rect.y0 + ff["cm_size_baseline"]), unit, fontsize=big, fontname="arialb", color=BLACK)
    else:
        centered(size_txt, "arialb", big, ff["cm_size_baseline"])
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
    composition always starts a new Pad), at most `max_units` of the biggest
    Pad template per Pad page.
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
    """Smallest Pad template that has enough Front side 1 slots."""
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
    pad_doc = fitz.open(_find_template(pad_cfg["template"]))
    page = pad_doc[0]
    comp = mapping["composition"]
    panels = build_text_panels(pad_cfg, mapping, len(group_rows))

    care_text, skup_text, tail_text = split_composition(group_rows[0].get("Composition_Care", ""), comp)
    wrap = lambda t: wrap_composition(t, fonts, comp["font_size"], comp["wrap_width"],
                                      comp.get("wide_prefixes", ()), comp.get("wide_width"))
    flow, last_idx = flow_into_panels(wrap(care_text), wrap(skup_text), wrap(tail_text),
                                      mapping, panels)   # may raise CareLabelOverflow

    fonts.register(page)
    _fill_pad_header(page, group_rows, mapping)

    tpl = mapping["templates"]
    # ---- Front side 1 slots (one per size) + caption over the last slot ----
    slot_rects = front1_rects(pad_cfg, mapping)
    front1_tpl = _find_template(tpl["front1"])
    for rect_coords, row in zip(slot_rects, group_rows):
        rect = fitz.Rect(rect_coords)
        _show(page, rect, front1_tpl)
        _draw_number(page, fonts, rect, 1, mapping)
        _draw_front1_fields(page, fonts, rect, row, mapping)
    _draw_caption(page, fonts, fitz.Rect(slot_rects[len(group_rows) - 1]), "Front side 1", mapping)

    # ---- text panels, only as many as the text needs ----
    email_cfg = mapping["email"]
    email_tpl = _find_template(email_cfg["template"])
    for i, panel in enumerate(panels):
        if i > last_idx:
            break
        rect = fitz.Rect(panel["rect"])
        key = tpl["back1"] if panel["name"] == "back1" else tpl[panel["kind"]]
        _show(page, rect, _find_template(key))
        _draw_caption(page, fonts, rect,
                      ("Front side " if panel["kind"] == "front" else "Back side ") + str(panel["number"]),
                      mapping)
        if panel["kind"] == "front":
            _draw_number(page, fonts, rect, panel["number"], mapping)
        _draw_lines(page, fonts, rect, flow.get(panel["name"], []), mapping)
        if i == last_idx:   # customer@pepco.eu artwork: 10 mm above the bottom of the LAST panel
            ex0, ey0, ex1, ey1 = email_cfg["rect"]
            _show(page, fitz.Rect(rect.x0 + ex0, rect.y0 + ey0, rect.x0 + ex1, rect.y0 + ey1), email_tpl)

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
