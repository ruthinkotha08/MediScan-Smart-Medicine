import streamlit as st
from datetime import date, datetime

st.set_page_config(
    page_title="MediScan — Smart Medicine Verification",
    page_icon="💊",
    layout="wide",
)

# Demo medicine database
# Replace these fictional records with verified medicine data later.
MEDICINES = {
    "MED001": {
        "name": "DemoCure 500",
        "ingredient": "Sample active ingredient",
        "manufacturer": "MediScan Demo Pharma",
        "mfg": "2025-01-15",
        "expiry": "2027-01-14",
        "batch": "MS-A1025",
        "form": "Tablet",
        "use": "Sample record demonstrating a simple explanation of the medicine's general labeled use.",
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
        "use": "Sample record demonstrating a plain-language explanation of a medicine's general purpose.",
        "warning": "Check the official label for contraindications, interactions, dosage and other warnings.",
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
        "warning": "This demo product is expired.",
    },
}

if "cabinet" not in st.session_state:
    st.session_state.cabinet = []


# -----------------------------
# CSS
# -----------------------------

st.markdown("""
<style>

.main-title {
    font-size: 3.2rem;
    font-weight: 800;
    margin-bottom: 5px;
}

.subtitle {
    font-size: 1.1rem;
    color: #64748b;
    line-height: 1.6;
}

.small-label {
    color: #1769e0;
    font-size: 0.8rem;
    font-weight: 800;
    letter-spacing: 2px;
}

</style>
""", unsafe_allow_html=True)


# -----------------------------
# Header
# -----------------------------

st.markdown(
    '<p class="small-label">SMART MEDICINE SAFETY</p>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="main-title">Scan. Verify. Understand.</div>',
    unsafe_allow_html=True
)

st.markdown(
    """
    <p class="subtitle">
    Scan a medicine QR code and view its product information,
    manufacturing date, expiry date, batch details and safety information.
    </p>
    """,
    unsafe_allow_html=True
)

st.divider()


# -----------------------------
# QR Scanner
# -----------------------------

st.subheader("📷 Scan Medicine QR Code")

st.info(
    "For the prototype, the QR code should contain a medicine ID such as "
    "MED001, MED002 or MED003."
)

try:

    from streamlit_camera_input_live import camera_input_live

    camera_image = camera_input_live(
        key="medicine_camera",
        text="Point your camera at the medicine QR code"
    )

    if camera_image is not None:
        st.success(
            "Camera is active. If your QR value is not detected automatically, "
            "use the Product ID field below."
        )

except ImportError:

    st.warning(
        "Camera component is not installed. "
        "Use the Product ID field below."
    )


# -----------------------------
# Product ID
# -----------------------------

st.subheader("⌨️ Medicine Product ID")

medicine_id = st.text_input(
    "Enter the value stored in the QR code",
    placeholder="Example: MED001"
).strip().upper()


demo = st.selectbox(
    "Or choose a demo medicine",
    [
        "Select...",
        "MED001",
        "MED002",
        "MED003"
    ]
)

if demo != "Select...":
    medicine_id = demo


# -----------------------------
# Medicine Lookup
# -----------------------------

medicine = MEDICINES.get(medicine_id)

if medicine_id and medicine is None:

    st.error(
        "Medicine ID not found. Try MED001, MED002 or MED003."
    )


# -----------------------------
# Medicine Result
# -----------------------------

if medicine:

    expiry_date = datetime.strptime(
        medicine["expiry"],
        "%Y-%m-%d"
    ).date()

    expired = expiry_date < date.today()

    st.divider()

    st.subheader("💊 Verified Product Record")

    if expired:

        st.error("🔴 EXPIRED MEDICINE")

    else:

        st.success("🟢 VALID MEDICINE RECORD")

    st.markdown(
        f"## {medicine['name']}"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.markdown("**Active ingredient**")
        st.write(medicine["ingredient"])

        st.markdown("**Manufacturer**")
        st.write(medicine["manufacturer"])

    with col2:

        st.markdown("**Manufacturing date**")

        st.write(
            datetime.strptime(
                medicine["mfg"],
                "%Y-%m-%d"
            ).strftime("%d %b %Y")
        )

        st.markdown("**Expiry date**")

        st.write(
            expiry_date.strftime("%d %b %Y")
        )

    with col3:

        st.markdown("**Batch number**")
        st.write(medicine["batch"])

        st.markdown("**Dosage form**")
        st.write(medicine["form"])


    # General use

    st.info(
        f"### 💡 General Use\n{medicine['use']}"
    )


    # Warning

    if expired:

        st.error(
            f"""
            ### ⚠️ Expiry Alert

            This medicine expired on
            **{expiry_date.strftime("%d %b %Y")}**.
            """
        )

    else:

        st.warning(
            f"""
            ### ⚠️ Safety Information

            {medicine['warning']}
            """
        )


    # Add to cabinet

    if st.button(
        "➕ Add to My Medicines",
        type="primary"
    ):

        existing_batches = [
            item["batch"]
            for item in st.session_state.cabinet
        ]

        if medicine["batch"] not in existing_batches:

            st.session_state.cabinet.append(
                medicine
            )

            st.success(
                "Medicine added to My Medicines."
            )

        else:

            st.info(
                "This medicine is already saved."
            )


# -----------------------------
# My Medicines
# -----------------------------

st.divider()

st.subheader("💊 My Medicines")

if st.session_state.cabinet:

    for item in st.session_state.cabinet:

        expiry = datetime.strptime(
            item["expiry"],
            "%Y-%m-%d"
        ).date()

        if expiry < date.today():

            st.error(
                f"""
                🔴 **{item['name']}**

                Batch: {item['batch']}

                Expired:
                {expiry.strftime("%d %b %Y")}
                """
            )

        else:

            st.success(
                f"""
                🟢 **{item['name']}**

                Batch: {item['batch']}

                Expires:
                {expiry.strftime("%d %b %Y")}
                """
            )

else:

    st.caption(
        "No medicines saved yet."
    )


# -----------------------------
# Features
# -----------------------------

st.divider()

st.subheader("How MediScan Works")

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.markdown("### 📷 QR")
    st.write(
        "Read a medicine product identifier."
    )

with c2:

    st.markdown("### 📅 Expiry")
    st.write(
        "Automatically check the recorded expiry date."
    )

with c3:

    st.markdown("### 🧠 Explain")
    st.write(
        "Show medicine information in simple language."
    )

with c4:

    st.markdown("### ⚠️ Alert")
    st.write(
        "Clearly flag expired medicine records."
    )


# -----------------------------
# Disclaimer
# -----------------------------

st.divider()

st.caption(
    """
    MediScan is an educational prototype.
    Demo medicine records are fictional.
    A production version must use validated, authoritative medicine data.
    MediScan does not diagnose conditions or replace professional medical advice.
    """
)
