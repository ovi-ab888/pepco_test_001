# ================================================================
#  price_helpers.py
#  PLN price parse + PLN theke baki currency (price ladder) bosano
#  app.py te use korte:
#      from price_helpers import parse_pln_price, apply_price_columns
# ================================================================
import streamlit as st

from data_loaders import load_price_data

# PLN chhara baki je currency column gulo DataFrame e boshbe
CURRENCY_COLUMNS = ['EUR', 'BGN', 'BAM', 'RON', 'CZK', 'UAH', 'MKD', 'RSD', 'HUF']


# ================================================================
#  Format numbers (PLN, EUR, RON, etc)
# ================================================================
def format_number(value, currency):
    """Format numeric pricing based on currency."""
    try:
        if isinstance(value, str):
            value = float(value.replace(',', '.'))

        if currency in ['EUR', 'BGN', 'BAM', 'RON', 'PLN']:
            formatted = f"{float(value):,.2f}".replace(".", ",")

            if ',' in formatted:
                parts = formatted.split(',')
                parts[0] = parts[0].replace('.', '')  # remove thousand separator
                formatted = ','.join(parts)

            return formatted

        return str(int(float(value)))

    except (ValueError, TypeError):
        return str(value)


# ================================================================
#  Match PLN to price ladder
# ================================================================
def find_closest_price(pln_value):
    """Returns matching row of other currencies for the PLN price."""
    try:
        price_data = load_price_data()

        if not price_data or 'PLN' not in price_data:
            st.error("❌ Price data not available")
            return None

        pln_value = float(pln_value)
        ladder = price_data['PLN']

        if pln_value not in ladder:
            st.error(f"❌ PLN {pln_value} not found in price sheet.")
            return None

        idx = ladder.index(pln_value)

        return {
            currency: format_number(values[idx], currency)
            for currency, values in price_data.items()
            if currency != 'PLN'
        }

    except Exception as e:
        st.error(f"Invalid price value: {str(e)}")
        return None


# ================================================================
#  Parse PLN price (UI text input theke)
# ================================================================
def parse_pln_price(raw_text):
    """Text theke PLN price float e convert kore. Invalid/empty hole None."""
    pln_price = None
    if raw_text.strip():
        try:
            pln_price = float(raw_text.replace(",", "."))
            if pln_price < 0:
                st.error("❌ Price can't be negative.")
                pln_price = None
        except ValueError:
            st.error("❌ Please enter a valid number like 12.50 or 12,50")
            pln_price = None
    return pln_price


# ================================================================
#  DataFrame e currency column gulo bosano
#  Return: True (bosheche)  /  False (price ladder e paoa jay ni)
# ================================================================
def apply_price_columns(df, pln_price):
    currency_values = find_closest_price(pln_price)

    if not currency_values:
        return False

    for cur in CURRENCY_COLUMNS:
        df[cur] = currency_values.get(cur, "")

    df['PLN'] = format_number(pln_price, 'PLN')
    return True
