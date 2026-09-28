import streamlit as st
from datetime import date, datetime

st.set_page_config(
    page_title="MediScan — Smart Medicine Verification",
    page_icon="💊",
    layout="wide",
)

# Demo database — fictional records for the prototype.
MEDICINES = {
    "MED001": {
        "name": "DemoCure 500",
        "ingredient": "Sample active ingredient",
        "manufacturer": "MediScan Demo Pharma",
        "mfg": "2025-01-15",
        "expiry": "2027-01-14",
        "batch": "MS-A1025",
        "form": "Tablet",
        "use": "Sample record: demonstrates how a medicine's general labeled use can be explained in simple language.",
        "warning": "Follow the product label and prescription. This demo record is not medical advice.",
    },
    "MED002": {
        "name": "DemoRelief 10",
        "ingredient": "Sample active ingredient",
        "manufacturer": "MediScan Demo Pharma",
        "mfg": "2026-02-01",
        "expiry": "2028-01-31",
        "batch": "MS-B2206",
        "form": "Tablet",
        "use": "Sample record: demonstrates a plain-language explanation of a medicine's general purpose.",
        "warning": "Check the official label for contraindications, interactions, dosage, and other warnings.",
    },
    "MED003": {
        "name": "ExpiredDemo 250",
        "ingredient": "Sample active ingredient",
        "manufacturer": "MediScan Demo Pharma",
        "mfg": "2023-03-01",
        "expiry": "2025-02-28",
        "batch": "MS-X2303",
        "form": "Capsule",
        "use": "Sample record used to demonstrate expiry detection.",
        "warning": "This demo product is expired. In a real system, the application should clearly flag it.",
    },
}

if "cabinet" not in st.session_state:
    st.session_state.cabinet = []

st.markdown("""
<style>
.main-title {font-size: 3.2rem; font-weight: 800; margin-bottom: 0.2rem;}
.subtitle {font-size: 1.15rem; color: #64748b; line-height: 1.6;}
.card {padding: 1.2rem; border: 1px solid #e2e8f0; border-radius: 14px;
       background: #ffffff; margin-bottom: 1rem;}
.small-label {color:#64748b; font-size:.8rem; font-weight:700; text-transform:uppercase;}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="small-label">SMART MEDICINE SAFETY</p>', unsafe_allow_html=True)
st.markdown('<div class="main-title">Scan. Verify. Understand.</div>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">MediScan helps users view medicine product information, '
    'manufacturing and expiry dates, batch details, and safety information from a QR/product ID.</p>',
    unsafe_allow_html=True
)

st.divider()

st.subheader("📱 Scan / Enter Medicine QR")
st.write("For this prototype, enter the product ID encoded in the QR code.")

col1, col2 = st.columns([2, 1])

with col1:
    medicine_id = st.text_input(
        "Medicine QR / Product ID",
        placeholder="Example: MED001",
        label_visibility="visible",
    ).strip().upper()

with col2:
    demo_choice = st.selectbox(
        "Or choose a demo",
        ["Select...", "MED001 — Medicine A", "MED002 — Medicine B", "MED003 — Expired"],
    )

if demo_choice != "Select...":
    medicine_id = demo_choice.split(" ")[0]

# Camera-based QR scanning can be added later with a Streamlit-compatible QR component.
# For the initial public prototype, QR/product ID entry is intentionally reliable and simple.

medicine = MEDICINES.get(medicine_id)

if medicine_id and medicine is None:
    st.error("Medicine ID not found in the demo database. Try MED001, MED002, or MED003.")

if medicine:
    expiry_date = datetime.strptime(medicine["expiry"], "%Y-%m-%d").date()
    expired = expiry_date < date.today()

    st.divider()
    st.subheader("💊 Verified Product Record")

    status_col, title_col = st.columns([1, 4])
    with status_col:
        if expired:
            st.error("🔴 EXPIRED")
        else:
            st.success("🟢 VALID")
    with title_col:
        st.markdown(f"## {medicine['name']}")

    a, b, c = st.columns(3)
    with a:
        st.metric("Active ingredient", medicine["ingredient"])
        st.metric("Manufacturer", medicine["manufacturer"])
    with b:
        st.metric("Manufacturing date", datetime.strptime(medicine["mfg"], "%Y-%m-%d").strftime("%d %b %Y"))
        st.metric("Expiry date", expiry_date.strftime("%d %b %Y"))
    with c:
        st.metric("Batch number", medicine["batch"])
        st.metric("Dosage form", medicine["form"])

    st.info(f"### 💡 What is it generally used for?\n{medicine['use']}")

    if expired:
        st.error(f"### ⚠️ Expiry Alert\nThis demo medicine expired on {expiry_date.strftime('%d %b %Y')}.")
    else:
        st.warning(f"### ⚠️ Safety information\n{medicine['warning']}")

    if st.button("➕ Add to My Medicines", type="primary"):
        if medicine["batch"] not in [x["batch"] for x in st.session_state.cabinet]:
            st.session_state.cabinet.append(medicine)
            st.success("Added to My Medicines.")
        else:
            st.info("This medicine is already in My Medicines.")

st.divider()

st.subheader("✨ How MediScan Works")
x1, x2, x3, x4 = st.columns(4)
with x1:
    st.markdown("### 📷 QR Identification")
    st.write("Identify a registered product or batch.")
with x2:
    st.markdown("### 📅 Expiry Verification")
    st.write("Compare the recorded expiry date with today's date.")
with x3:
    st.markdown("### 🧠 Simple Explanation")
    st.write("Present verified information in easy-to-understand language.")
with x4:
    st.markdown("### ⚠️ Safety Alerts")
    st.write("Clearly highlight expired products and important warnings.")

st.divider()

st.subheader("💊 My Medicines")
if st.session_state.cabinet:
    for item in st.session_state.cabinet:
        expiry = datetime.strptime(item["expiry"], "%Y-%m-%d").date()
        if expiry < date.today():
            st.error(f"🔴 **{item['name']}** — Batch {item['batch']} — Expired {expiry.strftime('%d %b %Y')}")
        else:
            st.success(f"🟢 **{item['name']}** — Batch {item['batch']} — Expires {expiry.strftime('%d %b %Y')}")
else:
    st.caption("No medicines saved yet.")

st.caption(
    "MediScan is an educational prototype. The demo records are fictional. "
    "A production version must use validated, authoritative medicine/product data. "
    "MediScan does not diagnose conditions or replace a prescription or qualified healthcare professional's advice."
)
