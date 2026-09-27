# ================================================================
#  translation.py
#  Multi-language product name (AL, ES, MK, etc) banano
#  app.py te use korte:
#      from translation import format_product_translations
# ================================================================
import pandas as pd


# ================================================================
#  TRANSLATION FORMATTER (AL, ES, MK, etc)
# ================================================================
def format_product_translations(
    product_name,
    translation_row,
    selected_materials=None,
    material_translations=None,
    material_compositions=None
):
    """Builds multilingual product description with material info."""
    formatted = []

    # Country suffix rules
    country_suffixes = {
        'BiH': " Sastav materijala na ušivenoj etiketi.",
        'RS': " Sastav materijala nalazi se na ušivenoj etiketi.",
        'UA': " Імпортер приймає претензії. Термін придатності – необмежений, якщо продукт використовується за призначенням (якщо на упаковці або продукті не вказано термін придатності). Умови зберігання – Зберігати в сухому місці при кімнатній температурі.",
    }

    # EN fallback
    en_text = translation_row.get('EN', product_name)
    formatted.append(f"|EN| {en_text}")

    # ES / ES_CA combined
    combined_lang = {
        'ES': (
            f"{translation_row['ES']} / {translation_row['ES_CA']}"
            if pd.notna(translation_row.get('ES_CA'))
            else translation_row.get('ES')
        )
    }

    # Language order defined
    language_order = [
        'AL', 'BG', 'BiH', 'CZ', 'DE', 'EE',
        'ES', 'GR', 'HR', 'HU', 'IT', 'LT',
        'LV', 'MK', 'PL', 'PT', 'RO', 'RS',
        'SI', 'SK', 'UA'
    ]

    # Build translations
    for lang in language_order:
        if lang in combined_lang and combined_lang[lang] is not None:
            text = combined_lang[lang]
        else:
            text = translation_row.get(lang, product_name)

        # Material names or composition for AL + MK only
        if selected_materials and material_translations and lang in ['AL', 'MK']:
            comp = (material_compositions or {}).get(lang, "")
            names = material_translations.get(lang, "")

            if comp:
                text = f"{text}: {comp}"
            elif names:
                text = f"{text}: {names}"

        # Country suffix
        if lang in country_suffixes:
            if not text.endswith('.'):
                text += "."
            text += country_suffixes[lang]

        formatted.append(f"|{lang}| {text}")

    return " ".join(formatted)
