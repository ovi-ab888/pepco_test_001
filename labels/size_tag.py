"""
labels/size_tag.py
Size Tag stickers — templates live in a folder tree on disk:

    templates/Sizetag/<Type>/<Department>/<Customer>/<size file>.pdf

e.g. templates/Sizetag/Regular/PB & PG/All/Size Tag.pdf

The available Type / Department / Customer / size-file options are
discovered at RUNTIME by scanning this folder tree — adding a new
combination is just dropping a new folder/PDF into templates/Sizetag/ on
GitHub, no code changes needed here or in app.py.

All Sizetag PDFs share the same header layout (Order ID, Item, Style Code,
Color, Designer, etc. — same positions as pad_header_mapping.json) plus
Item_name_English repeated across the 6 size panels, so they all use the
one config/size_tag_mapping.json.
"""
import os
import json
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from engine.label_engine import fill_single_label, generate_multipage_pdf

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
SIZETAG_ROOT = os.path.join(BASE_DIR, "templates", "Sizetag")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "size_tag_mapping.json")

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


def list_types() -> list:
    """Level 1: e.g. ['Regular', 'With OEKO-TEX']"""
    return _list_subfolders(SIZETAG_ROOT)


def list_departments(type_name: str) -> list:
    """Level 2: e.g. ['PB & PG', 'OB & OG']"""
    return _list_subfolders(os.path.join(SIZETAG_ROOT, type_name))


def list_customers(type_name: str, department: str) -> list:
    """Level 3: e.g. ['All', 'K. C. PRINT LTD.']"""
    return _list_subfolders(os.path.join(SIZETAG_ROOT, type_name, department))


def list_sizes(type_name: str, department: str, customer: str) -> list:
    """Level 4: the actual PDF filenames, e.g. ['Size Tag.pdf']"""
    return _list_pdfs(os.path.join(SIZETAG_ROOT, type_name, department, customer))


def get_template_path(type_name: str, department: str, customer: str, size_file: str) -> str:
    return os.path.join(SIZETAG_ROOT, type_name, department, customer, size_file)


def load_field_config() -> list:
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def generate_single(row: dict, template_path: str) -> bytes:
    field_config = load_field_config()
    return fill_single_label(template_path, row, field_config)


def generate_batch(rows: list, template_path: str) -> bytes:
    """rows = list of Excel row dicts. template_path = the specific PDF
    chosen via the Type/Department/Customer/Size cascade (use
    get_template_path() to build it)."""
    field_config = load_field_config()
    return generate_multipage_pdf(template_path, rows, field_config)
