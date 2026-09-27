# ================================================================
#  constants.py
#  CONSTANTS & MAPPINGS
#  app.py / onno file e use korte:
#      from constants import WASHING_CODES, COLLECTION_MAPPING
# ================================================================

# ---------------- Washing codes ----------------
WASHING_CODES = {
    '1': '১২৩৪৫', '2': '১৪৭৮৫', '3': 'djnst', '4': 'djnpt', '5': 'djnqt',
    '6': 'djnqt', '7': 'gjnpt', '8': 'gjnpu', '9': 'gjnqt', '10': 'gjnqu',
    '11': 'ijnst', '12': 'ijnsu', '13': 'ijnpu', '14': 'ijnsv', '15': 'djnsw'
}


# ---------------- Collection mapping ----------------
# Key = classification type (get_classification_type() er return value)
# Value = { PDF-er collection name : notun collection name }
COLLECTION_MAPPING = {
    # ---------------- Baby Girls ----------------
    "a": {  # baby girls outerwear
        "CUTE BEAR": "MODERN 1",
        "SUMMER CHERRY": "ROMANTIC 1",
        "AUTUMN": "ROMANTIC 2",
    },

    "d_girls": {  # baby girls essentials
        "FLOWER MOUSE": "MODERN 1",
        "LITTEL FOREST": "ROMANTIC 1",
    },

    # ---------------- Baby Boys ----------------
    "b": {  # baby boys outerwear
        "DOGS&FRIENDS": "MODERN 1",
        "EXPOLORE THE MOUNTINE": "MODERN 2",
        "SUMMER FUN": "MODERN 4",
        "COOL TRIP": "CLASSIC 1",
        "COLLEGE BEARS": "CLASSIC 1",
    },

    "d": {  # baby boys essentials
        "DOGS FRIENDS": "CLASSIC 1",
        "FOREST STORY": "MODERN 1",
        "LITTLE DREAMER": "MODERN 1",
        "X-MAS": "CLASSIC 2",
    },

    # ---------------- Younger Girls ----------------
    "yg": {  # younger girls outerwear
        "BFF’S CLUB": "COLLECTION_1",
        "LOVELY GIRL": "COLLECTION_2",
        "MEADOWLANDS": "COLLECTION_3",
        "EASTER ELEGANT": "COLLECTION_4",
        "HOT_COUNTRIES_Santorini": "COLLECTION_5",
        "READ_FRUITS": "COLLECTION_6",
        "SEA_SHELLL": "COLLECTION_7",
        "WILD_FOREST": "COLLECTION_7",
    },

    # ---------------- Older Girls ----------------
    "og": {  # older girls outerwear
        "xxxxx": "COLLECTION_0",
        "TRANSITIONAL LUMINOUS BLUME": "COLLECTION 1",
        "VALENTINE": "COLLECTION 2",
        "SOUVENIRE SNACK": "COLLECTION 3",
        "MY FAVOURITE THINGS": "COLLECTION 4",
        "CANDY": "COLLECTION 5",
        "SEASIDE": "COLLECTION 6",
        "LE SOLEI": "COLLECTION 7",
        "xxxxx": "COLLECTION 0",   # NOTE: "xxxxx" key duplicate - porer ta (COLLECTION 0) diye ager ta (COLLECTION_0) override hoy
    },

    # ---------------- Younger Boys ----------------
    "yb": {  # younger boys outerwear
        "FUNDAY CLUB": "COLLECTION_1",
        "DISCOVER DINO": "COLLECTION_2",
        "DOUBLE-TAKE": "COLLECTION_3",
        "EASTER ELEGANT": "COLLECTION_4",
        "SPORT": "COLLECTION_5",
        "MARITIME": "COLLECTION_6",
        "JUNGLE VIBES": "COLLECTION_7",
        "SURFING": "COLLECTION_8",
    },

    # ---------------- Older Boys ----------------
    "ob": {  # older boys outerwear
        "REBEL RIDER": "COLLECTION 1",
        "SKATE EPIC": "COLLECTION 2",
        "GAMER MODE": "COLLECTION 3",
        "SPORT": "COLLECTION 4",
        "SURFING": "COLLECTION 5",
    },

    # ---------------- Ladies ----------------
    "l": {  # ladies outerwear
        "XXXXX_1": "COLLECTION_1",
        "XXXXX_2": "COLLECTION_2",
        "XXXXX_3": "COLLECTION_3",
        "XXXXX_4": "COLLECTION_4",
        "XXXXX_5": "COLLECTION_5",
    },

    # ---------------- Mens ----------------
    "m": {  # mens outerwear
        "XXXXX_1": "COLLECTION_1",
        "XXXXX_2": "COLLECTION_2",
        "XXXXX_3": "COLLECTION_3",
        "XXXXX_4": "COLLECTION_4",
        "XXXXX_5": "COLLECTION_5",
    },
}
