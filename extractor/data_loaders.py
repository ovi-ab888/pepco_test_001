# ================================================================
#  data_loaders.py
#  Google Sheet theke data load korar function gulo
#  app.py te use korte:
#      from data_loaders import load_product_translations, load_material_translations
# ================================================================
import pandas as pd
import requests
import streamlit as st


# ================================================================
#  PRICE DATA LOADER (Google Sheet)
# ================================================================
@st.cache_data(ttl=600)
def load_price_data():
    """Load currency price ladder from Google Sheet."""
    try:
        url = (
            "https://docs.google.com/spreadsheets/d/e/"
            "2PACX-1vRdAQmBHwDEWCgmLdEdJc0HsFYpPSyERPHLwmr2tnTYU1BDWdBD6I0ZYfEDzataX0wTNhfLfnm-Te6w/"
            "pub?gid=583402611&single=true&output=csv"
        )
        df = pd.read_csv(url)

        if df.empty:
            st.error("Price data sheet is empty")
            return None

        # Convert to dictionary {currency: [values]}
        price_data = {}
        for currency in df.columns:
            price_data[currency] = df[currency].dropna().tolist()

        return price_data

    except Exception as e:
        st.error(f"Failed to load price data: {str(e)}")
        return None


# ================================================================
#  PRODUCT TRANSLATION LOADER
# ================================================================
@st.cache_data(ttl=600)
def load_product_translations():
    """Load product name translations from Google Sheet."""
    try:
        sheet_id = "1ue68TSJQQedKa7sVBB4syOc0OXJNaLS7p9vSnV52mKA"
        sheet_name = "SS26 Product_Name"
        encoded = requests.utils.quote(sheet_name)

        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded}"
        df = pd.read_csv(url)

        if df.empty:
            st.error("Loaded translations but sheet appears empty")

        return df

    except Exception as e:
        st.error(f"❌ Failed to load translations: {str(e)}")
        return pd.DataFrame()


# ================================================================
#  MATERIAL TRANSLATION LOADER
# ================================================================
@st.cache_data(ttl=600)
def load_material_translations():
    """Load material translations (AL, MK) with fallback."""
    try:
        url = (
            "https://docs.google.com/spreadsheets/d/e/"
            "2PACX-1vRdAQmBHwDEWCgmLdEdJc0HsFYpPSyERPHLwmr2tnTYU1BDWdBD6I0ZYfEDzataX0wTNhfLfnm-Te6w/"
            "pub?gid=1096440227&single=true&output=csv"
        )
        df = pd.read_csv(url)

        # Empty → go fallback
        if df.empty:
            st.warning("Material translations sheet empty — using fallback.")
            raise ValueError("Empty sheet")

        material_translations = []

        for _, row in df.iterrows():
            # Material name
            name = None
            if 'Name' in row and pd.notna(row['Name']):
                name = row['Name']
            else:
                try:
                    name = row.iloc[0]
                except Exception:
                    name = None

            if not name or pd.isna(name):
                continue

            # Add AL & MK groups
            for lang in ['AL', 'MK']:
                tr = row.get(lang, "")
                tr = "" if pd.isna(tr) else tr

                material_translations.append({
                    'material': name,
                    'language': lang,
                    'translation': tr
                })

        if not material_translations:
            raise ValueError("No material rows produced")

        return pd.DataFrame(material_translations)

    except Exception as e:
        # Fallback
        st.warning(f"Could not load material translations ({e}). Using fallback.")
        fallback = [
            {'material': 'Cotton', 'language': 'AL', 'translation': 'Cotton'},
            {'material': 'Cotton', 'language': 'MK', 'translation': 'Cotton'}
        ]
        return pd.DataFrame(fallback)
