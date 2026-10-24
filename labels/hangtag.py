"""
labels/hangtag.py  —  compatibility shim (AW27)
================================================
The old standalone copy of the Hangtag front code that used to live here is
obsolete (it still drew product_name). Everything now lives in:
    labels/hangtag_front.py   (prices)
    labels/hangtag_back.py    (Collection / Colour_SKU / Style / Batch / Cotton / barcode)
This file only re-exports the front-side API so any old `import labels.hangtag`
keeps working. If nothing imports it, you can simply delete this file.
"""
try:
    from .hangtag_front import *  # noqa: F401,F403
except ImportError:  # run as a plain script / labels/ on sys.path
    from hangtag_front import *  # noqa: F401,F403
