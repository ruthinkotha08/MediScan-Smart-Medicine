
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
    if not HINDSIGHT_API_KEY:
        st.session_state["hindsight_error"] = (
            "HINDSIGHT_API_KEY is missing. Add it to Streamlit Secrets."
        )
        return None

    if Hindsight is None:
        st.session_state["hindsight_error"] = (
            "The hindsight-client package is not installed. "
            "Add hindsight-client to requirements.txt and redeploy."
        )
        return None

    try:
        client = Hindsight(
            base_url=HINDSIGHT_BASE_URL,
            api_key=HINDSIGHT_API_KEY,
        )
        st.session_state["hindsight_error"] = ""
        return client
    except Exception as e:
        st.session_state["hindsight_error"] = (
            f"{type(e).__name__}: {e}"
        )
        return None


def ensure_hindsight_bank(client) -> bool:
    if client is None:
        return False
    try:
        client.create_bank(
            bank_id=HINDSIGHT_BANK_ID,
            name="MediScan Medicine Memory Agent",
            background=(
                "A medicine information assistant that remembers prior scan context, "
                "user explanation preferences, and previous medicine-information interactions. "
                "It must not diagnose, prescribe, or invent medicine facts."
            ),
            disposition={"skepticism": 4, "literalism": 5, "empathy": 4},
        )
    except Exception:
        # A 409/already-existing bank is expected on subsequent app starts.
        pass
    return True


hindsight = get_hindsight_client()
hindsight_ready = ensure_hindsight_bank(hindsight)
openai_client = get_openai_client()

# -----------------------------------------------------------------------------
# Hindsight memory layer
# -----------------------------------------------------------------------------
def retain_memory(content: str, context: str = "MediScan interaction") -> bool:
    if not hindsight_ready or hindsight is None:
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
