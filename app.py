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
        expiry = datetime.strptime(item["expiry"], "%Y-%m-%d").date()
        status = "🔴 Expired" if expiry < date.today() else "🟢 Current"
        st.markdown(
            f"**{item['name']}** · {status} · Batch `{item['batch']}` · Expires {expiry.strftime('%d %b %Y')}"
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
