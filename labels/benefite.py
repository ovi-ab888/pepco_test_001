"""
labels/benefite.py
"Benefite Tag and Sticker" — templates live in a nested folder tree:

    templates/Benefite/<Sticker Type>/<variant file>.pdf

e.g. templates/Benefite/KVI Size Sticker/Kids.pdf
     templates/Benefite/2-Pieces-Set/2-Pieces-Set.pdf

The folder name under templates/Benefite/ becomes the sticker-type name
shown as a checkbox in the UI. If that folder has more than one PDF inside,
those are variants (like KVI's Kids / Older Top / Older Top Bottom) and get
their own selector; a single-PDF folder just uses that one file directly.

Adding a new sticker type, or a new variant of an existing one, is just
dropping a new folder/PDF into templates/Benefite/ on GitHub — no code
changes needed here or in app.py.

NOTE: Inner & Outer Sticker is intentionally NOT part of this folder — it
stays its own separate, standalone item (labels/pad_label.py), not scanned
here.

All Benefite templates share the same header layout as Inner_Outer_Sticker/
Size Tag, so they use config/pad_header_mapping.json too — EXCEPT the
"Size" field (SIZE : ...) which is a Pad-specific multi-page thing; Benefite
items generally won't have TC_Number_stN variants, but if a template's row
does carry them, fill_single_label just skips any config field whose column
isn't present in that row, so it's harmless either way.
"""
import os
import json
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from engine.label_engine import fill_single_label, generate_multipage_pdf

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
BENEFITE_ROOT = os.path.join(BASE_DIR, "templates", "Benefite")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "pad_header_mapping.json")

# used only as a filename-logic fallback if nothing has been selected yet
TEMPLATE_PATH = None


def _list_subfolders(path: str) -> list:
    if not os.path.isdir(path):
        return []
    return sorted(d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d)))


def _list_pdfs(path: str) -> list:
    if not os.path.isdir(path):
        return []
    return sorted(f for f in os.listdir(path) if f.lower().endswith(".pdf"))


def list_sticker_types() -> list:
    """Folder names directly under templates/Benefite/ — each becomes a
    checkbox label, e.g. ['2-Pieces-Set', 'KVI Size Sticker', ...]"""
    return _list_subfolders(BENEFITE_ROOT)


def list_variants(sticker_type: str) -> list:
    """PDF filenames inside a sticker type's folder — e.g.
    ['Kids.pdf', 'Older Top.pdf', 'Older Top Bottom.pdf']"""
    return _list_pdfs(os.path.join(BENEFITE_ROOT, sticker_type))


def get_template_path(sticker_type: str, variant_file: str) -> str:
    return os.path.join(BENEFITE_ROOT, sticker_type, variant_file)


def load_field_config() -> list:
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def generate_single(row: dict, template_path: str) -> bytes:
    field_config = load_field_config()
    return fill_single_label(template_path, row, field_config)


def generate_batch(rows: list, template_path: str) -> bytes:
    """rows = list of Excel row dicts. template_path = the specific PDF
    chosen via the sticker-type/variant selection (use get_template_path())."""
    field_config = load_field_config()
    return generate_multipage_pdf(template_path, rows, field_config)
