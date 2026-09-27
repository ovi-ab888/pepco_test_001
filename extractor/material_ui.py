# ================================================================
#  material_ui.py
#  Material Composition (%) UI + AL/MK material translation
#  app.py te use korte:
#      from material_ui import render_material_section
# ================================================================
import streamlit as st


def render_material_section(material_translations_df):
    """Material dropdown + % input dekhay.
    Return: (selected_materials, cotton_value, material_trans_dict, material_compositions)
    """
    st.markdown("### Material Composition (%)")

    # Session init
    if "mat_rows" not in st.session_state:
        st.session_state.mat_rows = 1
    if "mat_data" not in st.session_state:
        st.session_state.mat_data = [{"mat": "Cotton", "pct": 100}]

    materials_list = (
        material_translations_df['material'].dropna().unique().tolist()
        if not material_translations_df.empty else []
    )
    if "Cotton" not in materials_list:
        materials_list = ["Cotton"] + materials_list

    def _ensure_row(i):
        while i >= len(st.session_state.mat_data):
            st.session_state.mat_data.append({"mat": None, "pct": 0})

    # ------ Per-row UI ------
    for i in range(st.session_state.mat_rows):
        _ensure_row(i)

        prev_total = sum(r["pct"] for r in st.session_state.mat_data[:i] if r["pct"])
        remain = max(0, 100 - prev_total)

        cA, cB = st.columns([3, 1.3])

        # Material select
        with cA:
            cur_mat = st.session_state.mat_data[i]["mat"]
            options = ["—"] + materials_list
            idx = options.index(cur_mat) if (cur_mat in options) else 0

            st.session_state.mat_data[i]["mat"] = st.selectbox(
                "Select Material(s)" if i == 0 else f"Select Material(s) #{i+1}",
                options,
                index=idx,
                key=f"mat_sel_{i}"
            )

        # Percentage input
        with cB:
            cur_pct = st.session_state.mat_data[i]["pct"]
            default_pct = (
                100 if (i == 0 and not cur_pct and st.session_state.mat_data[i]["mat"] == "Cotton")
                else min(cur_pct, remain)
            )

            if i == 0 and st.session_state.mat_data[i]["mat"] == "Cotton" and cur_pct in (None, 0):
                default_pct = 100
                st.session_state.mat_data[i]["pct"] = 100

            st.session_state.mat_data[i]["pct"] = st.number_input(
                "Composition (%)" if i == 0 else f"Composition (%) #{i+1}",
                min_value=0,
                max_value=remain,
                step=1,
                value=default_pct,
                key=f"mat_pct_{i}"
            )

    # Valid rows
    valid_rows = [
        r for r in st.session_state.mat_data[:st.session_state.mat_rows]
        if r["mat"] not in (None, "—") and r["pct"] > 0
    ]
    running_total = sum(r["pct"] for r in valid_rows)

    # Auto-add next material row
    if running_total < 100 and st.session_state.mat_rows < 5:
        last = st.session_state.mat_data[st.session_state.mat_rows - 1]
        if last["mat"] not in (None, "—") and last["pct"] > 0:
            st.session_state.mat_rows += 1
            _ensure_row(st.session_state.mat_rows - 1)
            st.rerun()

    # If total >= 100 → trim extra rows visually
    if running_total >= 100 and st.session_state.mat_rows > len(valid_rows):
        st.session_state.mat_rows = len(valid_rows)

    selected_materials = [r["mat"] for r in valid_rows]

    # Cotton flag
    cotton_value = ""
    if len(valid_rows) == 1:
        mat0 = (valid_rows[0]["mat"] or "").strip().lower()
        try:
            pct0_int = int(valid_rows[0]["pct"])
        except Exception:
            pct0_int = 0

        if mat0 == "cotton" and pct0_int == 100:
            cotton_value = "Z"

    # Info about totals
    if st.session_state.mat_rows == 1 and valid_rows and valid_rows[0]["pct"] == 100 and (
        valid_rows[0]["mat"] or ""
    ).lower() == "cotton":
        st.info("✅ 100% selected")
    elif running_total > 100:
        st.error("⚠️ Total exceeds 100%")

    st.write(f"**Total: {running_total}%**")

    # ============================================================
    #  Material Translation for AL / MK
    # ============================================================
    material_trans_dict = {}
    material_compositions = {}

    if selected_materials and not material_translations_df.empty:
        for lang in ['AL', 'MK']:
            names = []
            comp = []

            for r in valid_rows:
                t = material_translations_df[
                    (material_translations_df['material'] == r['mat']) &
                    (material_translations_df['language'] == lang)
                ]
                if not t.empty:
                    tr = t['translation'].iloc[0]
                    names.append(tr)
                    comp.append(f"{r['pct']}% {tr}")

            if names:
                material_trans_dict[lang] = ", ".join(names)
            if comp:
                material_compositions[lang] = ", ".join(comp)

    return selected_materials, cotton_value, material_trans_dict, material_compositions
