import base64
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
