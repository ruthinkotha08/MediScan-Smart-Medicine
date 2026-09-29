import base64
import hashlib
import json
import os
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import streamlit as st

# Optional dependencies are imported defensively so the app can still start
# when one integration is not configured.
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

try:
    from hindsight_client import Hindsight
except Exception:
    Hindsight = None


st.set_page_config(
    page_title="MediScan — Medicine Memory Agent",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Demo medicine data
# -----------------------------------------------------------------------------
MEDICINES: Dict[str, Dict[str, str]] = {
    "MED001": {
        "name": "DemoCure 500",
        "ingredient": "Sample active ingredient",
        "manufacturer": "MediScan Demo Pharma",
        "mfg": "2025-01-15",
        "expiry": "2027-01-14",
        "batch": "MS-A1025",
        "form": "Tablet",
        "use": "Demo record showing how a labeled general use can be explained in simple language.",
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
        "use": "Demo record showing a plain-language explanation of a medicine's general purpose.",
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
        "use": "Demo record used to demonstrate expiry detection.",
        "warning": "This demo product is expired. A real system should clearly flag it and direct the user to appropriate professional guidance.",
    },
}

# -----------------------------------------------------------------------------
# Styling
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    :root { --blue:#155EEF; --navy:#102A43; --green:#12B76A; --red:#D92D20; --muted:#667085; }
    .block-container { max-width: 1250px; padding-top: 2rem; }
    .hero { padding: 1.8rem 2rem; border-radius: 24px; background: linear-gradient(135deg,#eef6ff,#f7fbff 55%,#ecfdf3); border:1px solid #d9e7f7; }
    .eyebrow { color:var(--blue); font-weight:800; letter-spacing:2px; font-size:.78rem; margin-bottom:.25rem; }
    .hero h1 { font-size:3rem; margin:.1rem 0 .5rem; color:var(--navy); }
    .hero p { color:#475467; font-size:1.05rem; line-height:1.65; }
    .pill { display:inline-block; padding:.35rem .7rem; border-radius:999px; background:#e8f1ff; color:#155EEF; font-weight:700; font-size:.8rem; margin:.15rem; }
    .memory-card { padding:1rem 1.1rem; border:1px solid #dbe5f0; border-radius:16px; background:#fff; margin-bottom:.6rem; }
    .memory-on { border-left:5px solid #12B76A; background:#f6fffa; }
    .memory-off { border-left:5px solid #98A2B3; background:#f8fafc; }
    .metric-card { padding:1rem; border:1px solid #e4e7ec; border-radius:16px; background:#fff; }
    .small { color:#667085; font-size:.86rem; }
    .warning { padding:1rem; border-radius:14px; background:#fffaeb; border:1px solid #fedf89; }
    .danger { padding:1rem; border-radius:14px; background:#fef3f2; border:1px solid #fecdca; }
    .success { padding:1rem; border-radius:14px; background:#ecfdf3; border:1px solid #abefc6; }
    .flow { font-weight:800; color:#344054; text-align:center; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Session state
# -----------------------------------------------------------------------------
if "cabinet" not in st.session_state:
    st.session_state.cabinet = []
if "scan_history" not in st.session_state:
    st.session_state.scan_history = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "last_memory_context" not in st.session_state:
    st.session_state.last_memory_context = []
if "memory_profile" not in st.session_state:
    st.session_state.memory_profile = "demo-user-001"

# -----------------------------------------------------------------------------
# Config helpers
# -----------------------------------------------------------------------------
def secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, None)
        if value is not None:
            return str(value).strip()
    except Exception:
        pass
    return str(os.getenv(name, default) or default).strip()


OPENAI_API_KEY = secret("OPENAI_API_KEY")
OPENAI_MODEL = secret("OPENAI_MODEL", "gpt-5")
HINDSIGHT_API_KEY = secret("HINDSIGHT_API_KEY")
HINDSIGHT_BASE_URL = secret(
    "HINDSIGHT_BASE_URL",
    "https://api.hindsight.vectorize.io",
)
HINDSIGHT_BANK_ID = secret(
    "HINDSIGHT_BANK_ID",
    "mediscan-memory-agent",
)


@st.cache_resource(show_spinner=False)
def get_openai_client():
    if not OPENAI_API_KEY or OpenAI is None:
        return None
    try:
        return OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        return None


@st.cache_resource(show_spinner=False)
def get_hindsight_client():
    # Creating the client does not make a network request. Keep this at startup
    # so the Streamlit page can render even if Hindsight is temporarily unavailable.
    if not HINDSIGHT_API_KEY or Hindsight is None:
        return None

    try:
        return Hindsight(
            base_url=HINDSIGHT_BASE_URL,
            api_key=HINDSIGHT_API_KEY,
            timeout=15.0,
        )
    except Exception:
        return None


def ensure_hindsight_bank(client) -> bool:
    if client is None:
        return False

    if st.session_state.get("hindsight_bank_ready", False):
        return True

    try:
        client.create_bank(
            bank_id=HINDSIGHT_BANK_ID,
            name="MediScan Medicine Memory Agent",
            background=(
                "A medicine information assistant that remembers prior scan context, "
                "user explanation preferences, and previous medicine-information interactions. "
                "It must not diagnose, prescribe, or invent medicine facts."
            ),
            disposition={
                "skepticism": 4,
                "literalism": 5,
                "empathy": 4,
            },
        )
        st.session_state["hindsight_bank_ready"] = True
        st.session_state["hindsight_error"] = ""
        return True
    except Exception as e:
        # The bank may already exist. Verify usability with a recall request.
        try:
            client.recall(
                bank_id=HINDSIGHT_BANK_ID,
                query="MediScan connectivity check",
                max_tokens=100,
                budget="low",
            )
            st.session_state["hindsight_bank_ready"] = True
            st.session_state["hindsight_error"] = ""
            return True
        except Exception as verify_error:
            st.session_state["hindsight_error"] = (
                f"{type(e).__name__}: {e}; "
                f"verification: {type(verify_error).__name__}: {verify_error}"
            )
            return False


hindsight = get_hindsight_client()
hindsight_ready = hindsight is not None
openai_client = get_openai_client()

if "hindsight_bank_ready" not in st.session_state:
    st.session_state["hindsight_bank_ready"] = False
if "hindsight_error" not in st.session_state:
    st.session_state["hindsight_error"] = ""

# -----------------------------------------------------------------------------
# Hindsight memory layer
# -----------------------------------------------------------------------------
def retain_memory(content: str, context: str = "MediScan interaction") -> bool:
    if not hindsight_ready or hindsight is None:
        return False
    if not ensure_hindsight_bank(hindsight):
        return False
    try:
        hindsight.retain(
            bank_id=HINDSIGHT_BANK_ID,
            content=f"Profile: {st.session_state.memory_profile}. {content}",
            context=context,
            metadata={
                "app": "mediscan",
                "profile": st.session_state.memory_profile,
            },
        )
        return True
    except Exception as e:
        st.session_state["hindsight_error"] = (
            f"Retain failed: {type(e).__name__}: {e}"
        )
        return False


def recall_memories(query: str, limit: int = 6) -> List[str]:
    if not hindsight_ready or hindsight is None:
        return []
    if not ensure_hindsight_bank(hindsight):
        return []
    try:
        result = hindsight.recall(
            bank_id=HINDSIGHT_BANK_ID,
            query=f"Profile: {st.session_state.memory_profile}. {query}",
            max_tokens=2500,
            budget="low",
        )
        memories = []
        for item in result.results[:limit]:
            text = getattr(item, "text", None)
            if text:
                memories.append(text)
        return memories
    except Exception as e:
        st.session_state["hindsight_error"] = (
            f"Recall failed: {type(e).__name__}: {e}"
        )
        return []


# -----------------------------------------------------------------------------
# QR / image helpers
# -----------------------------------------------------------------------------
def decode_qr(image_bytes: bytes) -> Optional[str]:
    try:
        arr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if image is None:
            return None
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(image)
        return data.strip() if data else None
    except Exception:
        return None


def normalize_medicine_id(raw: str) -> str:
    raw = (raw or "").strip().upper()
    match = re.search(r"MED\d{3}", raw)
    return match.group(0) if match else raw


def ai_extract_medicine(image_bytes: bytes) -> Optional[Dict[str, Any]]:
    """Extract visible medicine-strip/label fields from an image.

    This is intentionally separate from QR decoding: a normal medicine strip may
    contain no QR code at all, so image extraction should still work.
    """
    if openai_client is None:
        return None

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    prompt = """
Read the medicine strip, box, bottle label, or prescription label in this image.
Extract ONLY information that is visibly printed. Do not guess or fill missing values.
Return strict JSON with exactly these keys:
medicine_name, ingredient, strength, dosage_form, manufacturer, batch,
mfg_date, exp_date, mrp, printed_use, confidence.

Important: This may be a medicine strip with NO QR code. Read the printed text directly.
Preserve the medicine name and strength exactly when visible. Dates may be printed as
MM/YYYY, MM-YYYY, DD/MM/YYYY, DD-MM-YYYY, or similar; preserve the visible date text.
Use null when a field is not visible. This is extraction, not medical diagnosis,
authenticity verification, or a recommendation.
"""
    try:
        response = openai_client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{b64}",
                            "detail": "high",
                        },
                    ],
                }
            ],
        )
        text = response.output_text.strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except Exception as e:
        st.session_state["image_extract_error"] = f"{type(e).__name__}: {e}"
        return None


def parse_label_date(value: Any) -> Optional[date]:
    """Parse common printed medicine dates without assuming a missing date."""
    if not value:
        return None
    text = str(value).strip()
    formats = (
        "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y",
        "%d-%b-%Y", "%d/%b/%Y", "%b-%Y", "%b/%Y", "%m-%Y", "%m/%Y",
    )
    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt)
            # For month-only expiry labels, use the last day of that month.
            if fmt in ("%b-%Y", "%b/%Y", "%m-%Y", "%m/%Y"):
                import calendar
                return date(parsed.year, parsed.month, calendar.monthrange(parsed.year, parsed.month)[1])
            return parsed.date()
        except ValueError:
            continue
    return None


def build_image_medicine(extracted: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert AI-extracted fields into the same display shape as demo records."""
    name = extracted.get("medicine_name")
    if not name:
        return None

    ingredient = extracted.get("ingredient") or "Not visible"
    strength = extracted.get("strength")
    if strength and str(strength).strip().lower() not in str(ingredient).lower():
        ingredient = f"{ingredient} ({strength})"

    return {
        "name": str(name).strip(),
        "ingredient": str(ingredient),
        "manufacturer": str(extracted.get("manufacturer") or "Not visible"),
        "mfg": str(extracted.get("mfg_date") or "Not visible"),
        "expiry": str(extracted.get("exp_date") or "Not visible"),
        "batch": str(extracted.get("batch") or "Not visible"),
        "form": str(extracted.get("dosage_form") or "Not visible"),
        "use": str(extracted.get("printed_use") or "No labeled use was clearly visible in the image."),
        "warning": "Image-extracted information is based only on visible printed text. Verify the physical label and use professional guidance for medical decisions.",
        "source": "image",
        "confidence": extracted.get("confidence"),
    }


# -----------------------------------------------------------------------------
# AI explanation / memory-aware agent
# -----------------------------------------------------------------------------
def generate_explanation(medicine: Dict[str, Any], memory_context: List[str]) -> str:
    base = (
        f"Medicine: {medicine.get('name', 'Unknown')}\n"
        f"Ingredient: {medicine.get('ingredient', 'Not available')}\n"
        f"General labeled use: {medicine.get('use', 'Not available')}\n"
        f"Safety information: {medicine.get('warning', 'Not available')}"
    )

    if openai_client is None:
        return medicine.get("use", "No AI explanation is configured. Please use the product label and qualified professional guidance.")

    memories = "\n".join(f"- {m}" for m in memory_context) if memory_context else "No prior memory is available."
    prompt = f"""
You are MediScan, a medicine-information assistant.
Explain the supplied product information in plain language.
Do not diagnose, prescribe, recommend a dose, or invent missing facts.
Use the remembered context only to personalize communication style or refer to prior scans.
Clearly say when a fact is unavailable.

CURRENT PRODUCT:
{base}

RELEVANT LONG-TERM MEMORY:
{memories}

Write 4 short sections:
1. What this product information says
2. Why the user might care about the batch/expiry fields
3. Safety notes from the supplied record
4. Memory-aware note: mention a prior scan/preference only if the memory actually supports it
"""
    try:
        response = openai_client.responses.create(model=OPENAI_MODEL, input=prompt)
        return response.output_text.strip()
    except Exception:
        return medicine.get("use", "AI explanation is temporarily unavailable.")


def answer_memory_question(question: str) -> str:
    memories = recall_memories(question, limit=8)
    st.session_state.last_memory_context = memories
    if not memories:
        return "I don't have a matching long-term memory for that question yet."

    if openai_client is None:
        return "\n".join(f"• {m}" for m in memories)

    context = "\n".join(f"- {m}" for m in memories)
    prompt = f"""
Answer the user's question using ONLY the retrieved MediScan memory below.
Do not invent medicine facts. If the memory does not answer the question, say so.
Do not diagnose or prescribe.

Retrieved memory:
{context}

Question: {question}
"""
    try:
        response = openai_client.responses.create(model=OPENAI_MODEL, input=prompt)
        return response.output_text.strip()
    except Exception:
        return "\n".join(f"• {m}" for m in memories)


# -----------------------------------------------------------------------------
# Header / hero
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">MEDICINE INFORMATION + PERSISTENT MEMORY</div>
      <h1>Scan. Remember. Understand.</h1>
      <p>
        MediScan turns a medicine scan into a continuing information workflow: capture the
        available product details, retain useful context, and recall it in later interactions.
      </p>
      <span class="pill">QR / IMAGE</span>
      <span class="pill">EXPIRY CHECK</span>
      <span class="pill">AI EXPLANATION</span>
      <span class="pill">HINDSIGHT MEMORY</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar: configuration and judge demo controls
with st.sidebar:
    st.markdown("## 🧠 Memory Agent")
    st.session_state.memory_profile = st.text_input(
        "Demo profile ID",
        value=st.session_state.memory_profile,
        help="Use the same profile ID during the demo so Hindsight can recall earlier interactions.",
    ).strip() or "demo-user-001"

    if hindsight_ready:
        if st.session_state.get("hindsight_bank_ready", False):
            st.success("Hindsight memory: connected")
        else:
            st.info("Hindsight memory: configured")
            st.caption("The memory bank will connect on the first memory action.")
        st.caption(f"Bank: `{HINDSIGHT_BANK_ID}`")
    else:
        st.error("Hindsight memory: NOT CONFIGURED")

        if not HINDSIGHT_API_KEY:
            st.caption("HINDSIGHT_API_KEY is missing from Streamlit Secrets.")
        elif Hindsight is None:
            st.caption(
                "hindsight-client is not installed. "
                "Add `hindsight-client` to requirements.txt and redeploy."
            )
        else:
            hindsight_error = st.session_state.get("hindsight_error", "")
            if hindsight_error:
                st.caption(f"Hindsight error: {hindsight_error}")
            else:
                st.caption(
                    "Hindsight client could not be initialized. "
                    "Check the API key and base URL."
                )

        st.caption(f"Base URL: `{HINDSIGHT_BASE_URL}`")

    if openai_client:
        st.success(f"AI analysis: {OPENAI_MODEL}")
    else:
        st.info("AI image analysis is optional. Demo records still work.")

    st.markdown("### Judge demo flow")
    st.markdown("1. Scan **MED001** → retain memory")
    st.markdown("2. Choose **Too technical** → retain preference")
    st.markdown("3. Scan **MED002** → retain second interaction")
    st.markdown("4. Ask: **What have I scanned before?**")
    st.markdown("5. Show the recalled memories")

    st.markdown("### Why Hindsight matters")
    st.caption("Without memory, each scan is isolated. With memory, the agent can recall prior scan context and communication preferences.")

# -----------------------------------------------------------------------------
# Main input area
# -----------------------------------------------------------------------------
st.markdown("## 1. Scan or upload a medicine")
left, right = st.columns(2)

with left:
    camera = st.camera_input("Take a photo of the QR code or medicine label")
    if camera is not None:
        camera_bytes = camera.getvalue()
        qr = decode_qr(camera_bytes)
        st.session_state.last_camera_bytes = camera_bytes
        st.session_state.image_source = "camera"
        if qr:
            st.session_state.last_qr = qr
            st.success(f"QR detected: `{qr}`")
        else:
            st.session_state.last_qr = ""
            st.info("No QR code found — automatically reading the printed medicine label instead.")

with right:
    upload = st.file_uploader(
        "Upload a QR/medicine image",
        type=["png", "jpg", "jpeg", "webp"],
    )
    if upload is not None:
        upload_bytes = upload.getvalue()
        qr = decode_qr(upload_bytes)
        st.session_state.last_upload_bytes = upload_bytes
        st.session_state.image_source = "upload"
        if qr:
            st.session_state.last_qr = qr
            st.success(f"QR detected: `{qr}`")
        else:
            st.session_state.last_qr = ""
            st.info("No QR code found — automatically reading the printed medicine label instead.")

# If no QR was found, automatically run image extraction once per image.
# This makes ordinary medicine strips work without requiring a QR code.
image_bytes_for_ai = st.session_state.get("last_upload_bytes") or st.session_state.get("last_camera_bytes")
if image_bytes_for_ai and openai_client and not st.session_state.get("last_qr"):
    image_hash = hashlib.sha256(image_bytes_for_ai).hexdigest()
    if st.session_state.get("ai_extracted_hash") != image_hash:
        with st.spinner("Reading the printed medicine label…"):
            extracted = ai_extract_medicine(image_bytes_for_ai)
        st.session_state["ai_extracted_hash"] = image_hash
        st.session_state["ai_extracted"] = extracted
        if extracted:
            st.success("Medicine label read successfully — no QR code was needed.")
        else:
            st.error("The medicine label could not be read reliably. Try a clearer, closer image.")

st.markdown("### Demo / fallback")
d1, d2, d3, d4 = st.columns(4)
with d1:
    if st.button("Demo MED001", use_container_width=True):
        st.session_state.last_qr = "MED001"
with d2:
    if st.button("Demo MED002", use_container_width=True):
        st.session_state.last_qr = "MED002"
with d3:
    if st.button("Demo expired", use_container_width=True):
        st.session_state.last_qr = "MED003"
with d4:
    manual = st.text_input("QR / ID", placeholder="MED001", label_visibility="collapsed")
    if manual:
        st.session_state.last_qr = manual

if st.session_state.get("ai_extracted"):
    with st.expander("AI-extracted fields", expanded=True):
        st.json(st.session_state.ai_extracted)

if st.session_state.get("image_extract_error"):
    with st.expander("Image extraction diagnostic"):
        st.code(st.session_state["image_extract_error"])

# -----------------------------------------------------------------------------
# Resolve result
# -----------------------------------------------------------------------------
raw_id = st.session_state.get("last_qr", "")
medicine_id = normalize_medicine_id(raw_id)
medicine = MEDICINES.get(medicine_id)

# If there is no QR/demo ID, use the medicine extracted from the image.
if not medicine and st.session_state.get("ai_extracted"):
    medicine = build_image_medicine(st.session_state["ai_extracted"])
    if medicine:
        medicine_id = "IMAGE-" + hashlib.sha1(medicine["name"].encode("utf-8")).hexdigest()[:8].upper()

if medicine:
    expiry_date = parse_label_date(medicine.get("expiry"))
    expired = expiry_date is not None and expiry_date < date.today()

    result = dict(medicine)
    result["id"] = medicine_id
    result["status"] = "EXPIRED" if expired else "VALID"
    st.session_state.last_result = result

    # Retain scan event only once per profile/batch in this session.
    event_key = f"{st.session_state.memory_profile}:{medicine_id}:{medicine['batch']}"
    if event_key not in st.session_state.scan_history:
        retained = retain_memory(
            content=(
                f"The user scanned medicine record {medicine_id}, named {medicine['name']}, "
                f"batch {medicine['batch']}, manufacturer {medicine['manufacturer']}, "
                f"manufacturing date {medicine['mfg']}, expiry date {medicine['expiry']}, "
                f"dosage form {medicine['form']}. Record status at scan time: {result['status']}."
            ),
            context="Medicine scan event",
        )
        st.session_state.scan_history.append(event_key)
        if retained:
            st.toast("🧠 Scan context retained in Hindsight", icon="🧠")

    st.divider()
    st.markdown("## 2. Scan result")
    if expiry_date is not None and expired:
        st.markdown(
            f'<div class="danger"><b>🔴 EXPIRED RECORD</b><br>The visible expiry date is {expiry_date.strftime("%d %b %Y")}.</div>',
            unsafe_allow_html=True,
        )
    elif expiry_date is not None:
        st.markdown(
            '<div class="success"><b>🟢 DATE CHECK PASSED</b><br>The recorded expiry date has not passed.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("Expiry date was not clearly available in the image, so no expiry status is inferred.")

    st.markdown(f"# {medicine['name']}")
    a, b, c = st.columns(3)
    with a:
        st.markdown("**Active ingredient**")
        st.write(medicine["ingredient"])
        st.markdown("**Manufacturer**")
        st.write(medicine["manufacturer"])
    with b:
        st.markdown("**Manufacturing date**")
        mfg_date = parse_label_date(medicine.get("mfg"))
        st.write(mfg_date.strftime("%d %b %Y") if mfg_date else medicine.get("mfg", "Not visible"))
        st.markdown("**Expiry date**")
        st.write(expiry_date.strftime("%d %b %Y") if expiry_date else medicine.get("expiry", "Not visible"))
    with c:
        st.markdown("**Batch number**")
        st.write(medicine["batch"])
        st.markdown("**Dosage form**")
        st.write(medicine["form"])

    if medicine.get("source") == "image":
        st.caption("📷 Details below were extracted from visible text in the uploaded medicine image. Verify them against the physical pack.")

    st.markdown("### Product information")
    st.info(medicine["use"])
    st.markdown(f'<div class="warning"><b>⚠ Safety information</b><br>{medicine["warning"]}</div>', unsafe_allow_html=True)

    # Memory-aware explanation
    st.markdown("## 3. What changed because the agent remembers?")
    memory_context = recall_memories(
        f"previous medicine scans, explanation preferences, and context relevant to {medicine['name']}",
        limit=5,
    )
    st.session_state.last_memory_context = memory_context

    off, on = st.columns(2)
    with off:
        st.markdown('<div class="memory-card memory-off"><b>WITHOUT MEMORY</b><br><br>This interaction is treated as a new, isolated scan. The explanation uses only the current record.</div>', unsafe_allow_html=True)
        st.caption("Generic context")
        st.write(medicine["use"])
    with on:
        st.markdown('<div class="memory-card memory-on"><b>WITH HINDSIGHT</b><br><br>The agent recalls relevant prior scan context and can adapt the explanation to what it has learned.</div>', unsafe_allow_html=True)
        if memory_context:
            explanation = generate_explanation(medicine, memory_context)
            st.write(explanation)
        else:
            st.caption("No matching long-term memory yet. Scan more than one medicine or save a preference to make the difference visible.")

    # Explicit learning signal
    st.markdown("### Teach the agent how you want explanations")
    f1, f2, f3 = st.columns(3)
    with f1:
        if st.button("👍 Keep it like this", use_container_width=True):
            if retain_memory("The user prefers the current concise explanation style.", "User feedback"):
                st.success("Preference retained.")
    with f2:
        if st.button("🧾 More detailed", use_container_width=True):
            if retain_memory("The user prefers more detailed explanations with structured sections.", "User feedback"):
                st.success("Preference retained.")
    with f3:
        if st.button("🧠 More simple", use_container_width=True):
            if retain_memory("The user prefers simpler, less technical explanations.", "User feedback"):
                st.success("Preference retained.")

    # Local cabinet for the current session
    if st.button("➕ Add to My Medicines", type="primary"):
        if medicine["batch"] not in [x["batch"] for x in st.session_state.cabinet]:
            st.session_state.cabinet.append(medicine)
            retain_memory(
                f"The user saved {medicine['name']} (batch {medicine['batch']}) to My Medicines.",
                "Medicine cabinet action",
            )
            st.success("Added to My Medicines and recorded in memory.")
        else:
            st.info("This medicine is already in the current session cabinet.")

elif medicine_id:
    st.warning("That medicine ID is not in the demo database. Try MED001, MED002, or MED003.")

# -----------------------------------------------------------------------------
# Memory assistant
# -----------------------------------------------------------------------------
st.divider()
st.markdown("## 4. Ask MediScan about what it remembers")
st.caption("This is the hackathon's key before/after interaction: ask about an earlier scan after the first interaction has been retained.")
question = st.text_input(
    "Memory question",
    placeholder="What medicines have I scanned before?",
)
if st.button("Recall from Hindsight", type="primary", disabled=not bool(question.strip())):
    with st.spinner("Recalling relevant memories…"):
        answer = answer_memory_question(question.strip())
    st.markdown('<div class="memory-card memory-on"><b>🧠 Hindsight recall</b></div>', unsafe_allow_html=True)
    st.write(answer)

if st.session_state.last_memory_context:
    with st.expander("Show retrieved memory evidence"):
        for idx, memory in enumerate(st.session_state.last_memory_context, 1):
            st.markdown(f"**Memory {idx}**")
            st.write(memory)

# -----------------------------------------------------------------------------
# My Medicines / workflow
# -----------------------------------------------------------------------------
st.divider()
st.markdown("## 5. My Medicines")
if st.session_state.cabinet:
    for item in st.session_state.cabinet:
        expiry = parse_label_date(item.get("expiry"))
        if expiry is None:
            status = "⚪ Expiry not available"
            expiry_text = str(item.get("expiry", "Not visible"))
        else:
            status = "🔴 Expired" if expiry < date.today() else "🟢 Current"
            expiry_text = expiry.strftime("%d %b %Y")
        st.markdown(
            f"**{item['name']}** · {status} · Batch `{item['batch']}` · Expires {expiry_text}"
        )
else:
    st.caption("No medicines saved in this session yet.")

st.divider()
st.markdown("## How the agent works")
q1, q2, q3, q4 = st.columns(4)
with q1:
    st.markdown('<div class="flow">01<br>SCAN</div>', unsafe_allow_html=True)
    st.caption("QR or medicine image")
with q2:
    st.markdown('<div class="flow">02<br>PROCESS</div>', unsafe_allow_html=True)
    st.caption("Extract available fields")
with q3:
    st.markdown('<div class="flow">03<br>RETAIN</div>', unsafe_allow_html=True)
    st.caption("Hindsight stores useful context")
with q4:
    st.markdown('<div class="flow">04<br>RECALL</div>', unsafe_allow_html=True)
    st.caption("Later interactions use memory")

st.markdown("### Hackathon story in one sentence")
st.info(
    "A normal medicine scanner forgets every interaction; MediScan adds a persistent memory layer so the agent can remember prior scans and communication preferences, then use that context in later interactions."
)

st.caption(
    "Educational prototype. Demo medicine records are fictional. This application does not establish product authenticity, diagnose conditions, or replace a qualified healthcare professional."
)
