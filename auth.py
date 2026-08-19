"""
auth.py
Simple username/password login gate for the app.

Credentials live in Streamlit secrets (NOT in code, NOT in git) — set them
in Streamlit Cloud under: Manage app -> Settings -> Secrets, like:

    [credentials]
    ovi = "your-password-here"
    staff = "another-password"

Each key under [credentials] is a valid username; its value is that user's
password. Add as many as you need.

For local testing, create a file .streamlit/secrets.toml with the same
content (this file should be in .gitignore, never committed).
"""
import streamlit as st


def check_login() -> bool:
    """
    Shows a login form if the user isn't authenticated yet. Returns True once
    logged in (and lets the rest of the app render); returns False and stops
    the script otherwise — call this at the very top of app.py:

        if not auth.check_login():
            st.stop()
    """
    if st.session_state.get("authenticated"):
        return True

    st.title("🔒 PEPCO Label Automation — Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", type="primary")

    if submitted:
        credentials = st.secrets.get("credentials", {})
        if not credentials:
            st.error("No credentials configured yet — add [credentials] to Streamlit secrets.")
            return False
        if username in credentials and credentials[username] == password:
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.rerun()
        else:
            st.error("Wrong username or password.")

    return False


def logout_button():
    """Optional: call this from the sidebar to let the user log out."""
    if st.session_state.get("authenticated"):
        with st.sidebar:
            st.caption(f"Logged in as **{st.session_state.get('username', '')}**")
            if st.button("Log out"):
                st.session_state["authenticated"] = False
                st.session_state.pop("username", None)
                st.rerun()
