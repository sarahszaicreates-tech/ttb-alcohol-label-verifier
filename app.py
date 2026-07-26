from pathlib import Path

import streamlit as st

from vesper.models import ExpectedLabel, Status
from vesper.ocr import OCRUnavailableError, run_local_ocr
from vesper.rules import AUTHORIZED_FILL_ML, validate_expected
from vesper.service import verify_label_text


st.set_page_config(page_title="Vesper Label Verifier", page_icon="◈", layout="wide")

st.markdown(
    """
    <style>
    .block-container {max-width: 1180px; padding-top: 2rem;}
    .eyebrow {letter-spacing:.14em;text-transform:uppercase;color:#8b6b32;
              font-size:.75rem;font-weight:700}
    .hero {font-size:2.45rem;font-weight:720;line-height:1.05;margin:.25rem 0}
    .subtle {color:#59635f;max-width:760px}
    div[data-testid="stMetric"] {background:#fff;border:1px solid #ddd6c9;
              padding:1rem;border-radius:14px}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="eyebrow">Human-in-the-loop compliance support</div>', unsafe_allow_html=True)
st.markdown('<div class="hero">Vesper Label Verifier</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtle">Compare a distilled-spirits application against label text '
    "using local OCR and deterministic U.S. TTB-focused rules.</div>",
    unsafe_allow_html=True,
)
st.warning(
    "Decision support only — this prototype does not issue or replace TTB label approval."
)

with st.sidebar:
    st.header("Expected application data")
    brand = st.text_input("Brand name", value="Vesper Reserve")
    class_type = st.text_input("Class/type", value="Vodka")
    abv = st.number_input("Alcohol by volume (%)", min_value=0.5, max_value=100.0, value=40.0, step=0.1)
    fills = sorted(AUTHORIZED_FILL_ML, reverse=True)
    default_index = fills.index(750)
    net_ml = st.selectbox("Net contents", fills, index=default_index, format_func=lambda x: f"{x} mL")
    st.caption("Current authorized standards of fill (TTB guidance updated May 21, 2026).")

expected = ExpectedLabel(brand, class_type, float(abv), int(net_ml))
errors = validate_expected(expected)

left, right = st.columns([1, 1], gap="large")
with left:
    st.subheader("1. Upload label")
    uploaded = st.file_uploader("PNG, JPG, JPEG, WEBP, or TIFF", type=["png", "jpg", "jpeg", "webp", "tif", "tiff"])
    if uploaded:
        image_bytes = uploaded.getvalue()
        st.image(image_bytes, caption=uploaded.name, use_container_width=True)

with right:
    st.subheader("2. Extract and verify")
    use_manual = st.checkbox("Use/paste label text instead of OCR", help="Useful for review or if OCR cannot read the image.")
    manual_text = st.text_area("Label text", height=250, disabled=not use_manual)
    can_run = bool(manual_text.strip()) if use_manual else uploaded is not None
    run = st.button("Verify label", type="primary", use_container_width=True, disabled=not can_run or bool(errors))

if errors:
    for error in errors:
        st.error(error)

if run:
    if use_manual:
        text, confidence, elapsed, provider = manual_text, None, 0.0, "Manual text"
    else:
        try:
            with st.spinner("Reading label locally…"):
                result = run_local_ocr(uploaded.getvalue())
            text, confidence, elapsed, provider = (
                result.text, result.confidence, result.elapsed_seconds, result.provider
            )
        except OCRUnavailableError as exc:
            st.error(str(exc))
            st.stop()

    if not text.strip():
        st.error("No readable text was extracted. Try a clearer image or use the manual-text option.")
        st.stop()

    report = verify_label_text(text, expected)
    st.divider()
    st.subheader("Verification result")
    palette = {
        Status.MATCH: ("✅", "Match"),
        Status.POSSIBLE_MATCH: ("🟡", "Possible match — review"),
        Status.MISMATCH: ("❌", "Mismatch"),
        Status.UNABLE: ("⚪", "Unable to determine"),
    }
    icon, label = palette[report.overall_status]
    m1, m2, m3 = st.columns(3)
    m1.metric("Overall", f"{icon} {label}")
    m2.metric("OCR provider", provider)
    m3.metric("Processing time", f"{elapsed:.2f}s")
    if confidence is not None:
        st.caption(f"Mean OCR confidence: {confidence:.1%}")

    for check in report.checks:
        check_icon = palette[check.status][0]
        with st.container(border=True):
            st.markdown(f"#### {check_icon} {check.field}")
            c1, c2 = st.columns(2)
            c1.markdown(f"**Expected**  \n{check.expected}")
            c2.markdown(f"**Observed**  \n{check.observed}")
            st.caption(check.explanation)

    with st.expander("Extracted OCR text"):
        st.code(text, language=None)
    with st.expander("What this prototype cannot certify"):
        st.markdown(
            "- Same-field-of-vision placement of brand, class/type, and alcohol content\n"
            "- Exact physical type size, bold styling, contrast, or continuous-paragraph layout\n"
            "- Whether a brand or designation is legally misleading\n"
            "- Product composition, formula, age statements, or conditional disclosures"
        )

st.divider()
st.caption(
    "Scope: distilled spirits only. Rules are based on 27 CFR parts 5 and 16 and "
    "official TTB distilled-spirits labeling guidance. Always complete human review."
)

