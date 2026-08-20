"""
theme.py
Loads static/css/style.css (same design system as plate_planner_app) so
this app matches it visually — dark/light mode, Inter font, card layout.
"""
import os
import streamlit as st

CSS_PATH = os.path.join(os.path.dirname(__file__), "static", "css", "style.css")


def load_css():
    with open(CSS_PATH, "r") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def main_header(title: str, subtitle: str = ""):
    """Matches the .main-header / .card-title classes from style.css."""
    st.markdown(
        f"""
        <div class="main-header">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
