# ================================================================
#  auto_fields.py
#  PDF-e nai, code nije generate kore ei field gulo:
#     today_date, Colour_SKU, Style_Merch_Season, Batch,
#     Dept, Item_name_English
# ================================================================
import re
from datetime import datetime, timedelta


# ================================================================
#  today_date  ->  ajker date (DD-MM-YYYY)
# ================================================================
def make_today_date():
    return datetime.today().strftime("%d-%m-%Y")


# ================================================================
#  Colour_SKU  ->  "WHITE • SKU 12345678"
# ================================================================
def make_colour_sku(colour, sku):
    return f"{colour} • SKU {sku}"


# ================================================================
#  Style_Merch_Season  ->  "STYLE 123456 • suffix • Batch No./"
# ================================================================
def make_style_merch_season(style_code, style_suffix=""):
    if not style_code:
        return "STYLE UNKNOWN"
    return f"STYLE {style_code} • {style_suffix} • Batch No./"


# ================================================================
#  Batch  ->  Handover date minus 20 din  ->  "виготовлення: MMYYYY"
#  handover_date: "dd/mm/YYYY" string (na thakle None)
# ================================================================
def make_batch(handover_date):
    batch = "UNKNOWN"
    if handover_date:
        try:
            batch_date = datetime.strptime(handover_date, "%d/%m/%Y")
            batch = (batch_date - timedelta(days=20)).strftime("%m%Y")
        except Exception:
            pass
    return f"виготовлення: {batch}"


# ================================================================
#  Dept  ->  BABY / KIDS / TEENS / WOMEN / MEN
# ================================================================
def get_dept_value(item_class):
    """Maps classification -> BABY / KIDS / TEENS / WOMEN / MEN."""
    if not item_class:
        return ""

    ic = item_class.lower()

    if any(x in ic for x in ['baby boys', 'baby girls']):
        return "BABY"
    if any(x in ic for x in ['younger boys', 'younger girls']):
        return "KIDS"
    if any(x in ic for x in ['older girls', 'older boys']):
        return "TEENS"
    if 'ladies outerwear' in ic:
        return "WOMEN"
    if 'mens outerwear' in ic:
        return "MEN"

    return ""


# ================================================================
#  Item_name_English  ->  clean + CAPITAL
# ================================================================
# Ei prefix gulo name-er shuru theke bad jabe.
# Lomba phrase age, chhoto porе (jate "baby girl basic" e shudhu "baby girl" kete na jay).
ITEM_NAME_PREFIXES = [
    "xxxxx",
    "xxxxx",
    "xxxxx",
    "xxxxx",
    "xxxxx",
    "xxxxx",
    "xxxxx",
    "xxxxx",
]


def clean_item_name_english(name: str) -> str:
    """
    Item_name_EN theke prefix gulo bad diye
    baki ongsho CAPITAL LETTERS e return kore.
    """
    if not isinstance(name, str):
        return ""

    text = name.strip()

    # shuru te "4." "12." er moto digit + dot thakle bad daw
    text = re.sub(r'^\d+\.\s*', '', text).strip()

    lower = text.lower()

    for p in ITEM_NAME_PREFIXES:
        if lower.startswith(p):
            cut_len = len(p)
            text = text[cut_len:].strip(" -_,./").strip()
            break

    return text.upper()
