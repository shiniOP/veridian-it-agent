import streamlit as st
import uuid
import re

from agent import run_agent


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Veridian Corp - AI Operations",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
<style>

/* ============================================================
   GLOBAL APP
   ============================================================ */

.stApp {
    background:
        radial-gradient(
            circle at 12% 0%,
            rgba(91, 76, 230, 0.13),
            transparent 30%
        ),
        radial-gradient(
            circle at 88% 0%,
            rgba(20, 184, 166, 0.07),
            transparent 28%
        ),
        #070b12;

    color: #e5e7eb;
}


/* ============================================================
   MAIN CONTAINER
   ============================================================ */

.main .block-container {
    max-width: 1280px;
    padding-top: 32px;
    padding-bottom: 120px;
}


/* ============================================================
   SIDEBAR
   ============================================================ */

section[data-testid="stSidebar"] {
    background: #090d14;
    border-right: 1px solid #1d2530;
}


section[data-testid="stSidebar"] > div {
    padding: 24px 20px;
}


/* ============================================================
   SIDEBAR BUTTONS
   ============================================================ */

section[data-testid="stSidebar"] .stButton > button {
    background: #10151d;
    border: 1px solid #202936;
    color: #c5cfdd;
    border-radius: 9px;
    font-size: 12px;
    min-height: 34px;
}


section[data-testid="stSidebar"] .stButton > button:hover {
    background: #161d28;
    border-color: #5b4ce6;
    color: #ffffff;
}


/* ============================================================
   SIDEBAR CARDS
   ============================================================ */

section[data-testid="stSidebar"]
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #10151d;
    border: 1px solid #222b37;
    border-radius: 14px;
}


/* ============================================================
   MAIN TITLE
   ============================================================ */

.main-title {
    font-size: 35px;
    font-weight: 800;
    letter-spacing: -1.2px;
    color: #f8fafc;
    line-height: 1.15;
}


.main-subtitle {
    font-size: 13px;
    color: #75849d;
    margin-top: 5px;
}


/* ============================================================
   WELCOME CARD
   ============================================================ */

[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: #202833;
    border-radius: 16px;
    background: rgba(12, 17, 25, 0.72);
}


/* ============================================================
   CHAT MESSAGES
   ============================================================ */

[data-testid="stChatMessage"] {
    background: rgba(15, 23, 42, 0.42);
    border: 1px solid rgba(148, 163, 184, 0.08);
    border-radius: 14px;
    margin-bottom: 12px;
}


/* ============================================================
   CHAT INPUT
   ============================================================ */

[data-testid="stChatInput"] {
    background: #0c1018;
}


[data-testid="stChatInput"] textarea {
    background: #151923 !important;
    color: #e2e8f0 !important;
    border: 1px solid #2a313e !important;
    border-radius: 12px !important;
}


/* ============================================================
   GENERAL BUTTONS
   ============================================================ */

.stButton > button {
    background: #10151d;
    border: 1px solid #232b37;
    color: #d2dae6;
    border-radius: 10px;
    transition: 0.15s ease;
}


.stButton > button:hover {
    background: #151c27;
    border-color: #5146d8;
    color: #ffffff;
}


/* ============================================================
   QUICK REQUEST BUTTONS
   ============================================================ */

.quick-request .stButton > button {
    height: 40px;
    font-size: 12px;
    background: #11161e;
    border: 1px solid #252d38;
}


/* ============================================================
   EXPANDERS
   ============================================================ */

[data-testid="stExpander"] {
    background: #0d121a;
    border: 1px solid #202833;
    border-radius: 10px;
}


/* ============================================================
   DIVIDERS
   ============================================================ */

hr {
    border-color: #1b222d;
}


/* ============================================================
   CAPTIONS
   ============================================================ */

.stCaption {
    color: #687790 !important;
}


/* ============================================================
   SUCCESS / INFO
   ============================================================ */

[data-testid="stAlert"] {
    border-radius: 10px;
}


/* ============================================================
   HIDE STREAMLIT BRANDING
   ============================================================ */

#MainMenu {
    visibility: hidden;
}


footer {
    visibility: hidden;
}


/* ============================================================
   SCROLLBAR
   ============================================================ */

::-webkit-scrollbar {
    width: 7px;
}


::-webkit-scrollbar-track {
    background: #080c12;
}


::-webkit-scrollbar-thumb {
    background: #252c38;
    border-radius: 10px;
}


</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

if "chats" not in st.session_state:
    st.session_state.chats = {}


if "active_chat" not in st.session_state:
    st.session_state.active_chat = None


if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None


# ============================================================
# CREATE NEW CHAT
# ============================================================

def create_new_chat():

    chat_id = str(uuid.uuid4())

    st.session_state.chats[chat_id] = {
        "title": "New conversation",
        "thread_id": chat_id,
        "messages": [],
        "request_count": 0,
    }

    st.session_state.active_chat = chat_id


# ============================================================
# DELETE INDIVIDUAL CHAT
# ============================================================

def delete_chat(chat_id):

    if chat_id in st.session_state.chats:

        del st.session_state.chats[chat_id]

    # If deleted chat was active
    if st.session_state.active_chat == chat_id:

        st.session_state.active_chat = None

        # Open most recent remaining chat
        if st.session_state.chats:

            remaining = list(
                st.session_state.chats.keys()
            )

            st.session_state.active_chat = (
                remaining[-1]
            )

        # If nothing remains, create new chat
        else:

            create_new_chat()


# ============================================================
# EXTRACT DECISION FIELD
# ============================================================

def extract_field(text, field):

    if not text:
        return "NONE"

    pattern = rf"^{re.escape(field)}:\s*(.+)$"

    match = re.search(
        pattern,
        text,
        re.IGNORECASE | re.MULTILINE,
    )

    if match:
        return match.group(1).strip()

    return "NONE"


# ============================================================
# CREATE FIRST CHAT
# ============================================================

if not st.session_state.chats:

    create_new_chat()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    # ========================================================
    # BRAND
    # ========================================================

    st.markdown(
        "## ◈ VERIDIAN"
    )

    st.caption(
        "INTERNAL IT SERVICES"
    )

    st.divider()


    # ========================================================
    # SYSTEM STATUS
    # ========================================================

    with st.container(border=True):

        st.caption(
            "SYSTEM STATUS"
        )

        st.markdown(
            "🟢 Agent Online"
        )

        st.markdown(
            "🟢 Knowledge Base Connected"
        )

        st.markdown(
            "🟢 Ticket Index Ready"
        )


    # ========================================================
    # ARCHITECTURE
    # ========================================================

    with st.container(border=True):

        st.caption(
            "AGENT ARCHITECTURE"
        )

        st.write(
            "**LangGraph**"
        )

        st.caption(
            "Retrieval → Decision → Response"
        )


    # ========================================================
    # INTELLIGENCE LAYER
    # ========================================================

    with st.container(border=True):

        st.caption(
            "INTELLIGENCE LAYER"
        )

        st.write(
            "**Gemini Multi-Model**"
        )

        st.caption(
            "2.5 Flash-Lite → "
            "3.1 Flash-Lite → "
            "3.5 Flash-Lite"
        )


    # ========================================================
    # CURRENT SESSION
    # ========================================================

    with st.container(border=True):

        st.caption(
            "CURRENT SESSION"
        )

        active_data = st.session_state.chats[
            st.session_state.active_chat
        ]

        st.write(
            f"**{active_data['request_count']} requests**"
        )

        st.caption(
            f"Thread: "
            f"{active_data['thread_id'][:12]}..."
        )


    # ========================================================
    # NEW CONVERSATION
    # ========================================================

    if st.button(
        "＋  New conversation",
        use_container_width=True,
    ):

        create_new_chat()

        st.rerun()


    st.divider()


    # ========================================================
    # RECENT CONVERSATIONS
    # ========================================================

    st.caption(
        "RECENT CONVERSATIONS"
    )


    chat_items = list(
        st.session_state.chats.items()
    )[::-1]


    for chat_id, chat in chat_items:

        left, right = st.columns(
            [5, 1],
            gap="small",
        )


        # ----------------------------------------------------
        # OPEN CHAT
        # ----------------------------------------------------

        with left:

            title = chat["title"]

            if len(title) > 24:

                title = (
                    title[:24]
                    + "..."
                )


            if (
                chat_id
                == st.session_state.active_chat
            ):

                title = (
                    "▸ "
                    + title
                )


            if st.button(
                title,
                key=f"open_chat_{chat_id}",
                use_container_width=True,
            ):

                st.session_state.active_chat = (
                    chat_id
                )

                st.rerun()


        # ----------------------------------------------------
        # DELETE CHAT
        # ----------------------------------------------------

        with right:

            if st.button(
                "×",
                key=f"delete_chat_{chat_id}",
                help="Delete this conversation",
            ):

                delete_chat(
                    chat_id
                )

                st.rerun()


# ============================================================
# ACTIVE CHAT
# ============================================================

current_chat = st.session_state.chats[
    st.session_state.active_chat
]


# ============================================================
# MAIN HEADER
# ============================================================

header_left, header_right = st.columns(
    [7, 3]
)


with header_left:

    st.caption(
        "VERIDIAN CORP  •  AI OPERATIONS"
    )

    st.markdown(
        '<div class="main-title">'
        'Internal IT Service Agent'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="main-subtitle">'
        'A policy-grounded AI assistant for resolving, '
        'routing and clarifying employee IT requests.'
        '</div>',
        unsafe_allow_html=True,
    )


with header_right:

    st.write("")

    status_left, status_right = st.columns(
        2
    )


    with status_left:

        st.success(
            "● SYSTEM ONLINE"
        )


    with status_right:

        st.info(
            "AI SUPPORT"
        )


st.divider()


# ============================================================
# WELCOME CARD
# ============================================================

with st.container(border=True):

    st.write("")

    st.markdown(
        "## ◈"
    )

    st.markdown(
        "### How can I help you today?"
    )

    st.caption(
        "Ask about VPN access, password resets, "
        "software installation, hardware replacement, "
        "printers, mailbox quotas, WFH equipment, "
        "security incidents and more."
    )

    st.write("")


# ============================================================
# QUICK REQUESTS
# ============================================================

st.caption(
    "QUICK REQUESTS"
)


quick1, quick2, quick3 = st.columns(
    3
)


with quick1:

    if st.button(
        "🔐  VPN credentials expired",
        use_container_width=True,
    ):

        st.session_state.pending_prompt = (
            "My VPN credentials have expired."
        )


with quick2:

    if st.button(
        "💻  Replace my laptop",
        use_container_width=True,
    ):

        st.session_state.pending_prompt = (
            "I want to request a laptop replacement."
        )


with quick3:

    if st.button(
        "📄  Install software",
        use_container_width=True,
    ):

        st.session_state.pending_prompt = (
            "I want to install software on my computer."
        )


quick4, quick5, quick6 = st.columns(
    3
)


with quick4:

    if st.button(
        "🖨️  Printer not working",
        use_container_width=True,
    ):

        st.session_state.pending_prompt = (
            "My printer is not working."
        )


with quick5:

    if st.button(
        "📧  Mailbox quota",
        use_container_width=True,
    ):

        st.session_state.pending_prompt = (
            "I need more mailbox storage."
        )


with quick6:

    if st.button(
        "🛡️  Report security issue",
        use_container_width=True,
    ):

        st.session_state.pending_prompt = (
            "I think I may have received a phishing email."
        )


# ============================================================
# DISPLAY EXISTING CONVERSATION
# ============================================================

if current_chat["messages"]:

    st.divider()

    st.caption(
        "CONVERSATION"
    )


# ============================================================
# RENDER MESSAGES
# ============================================================

for message in current_chat["messages"]:

    role = message["role"]

    content = message["content"]


    # ========================================================
    # USER MESSAGE
    # ========================================================

    if role == "user":

        with st.chat_message(
            "user",
            avatar="👤",
        ):

            st.write(
                content
            )


    # ========================================================
    # ASSISTANT MESSAGE
    # ========================================================

    else:

        with st.chat_message(
            "assistant",
            avatar="🤖",
        ):

            st.write(
                content
            )


            # ------------------------------------------------
            # DECISION INFORMATION
            # ------------------------------------------------

            decision_text = message.get(
                "decision",
                ""
            )


            if decision_text:

                decision = extract_field(
                    decision_text,
                    "DECISION",
                )


                category = extract_field(
                    decision_text,
                    "CATEGORY",
                )


                policies = extract_field(
                    decision_text,
                    "RELEVANT POLICIES",
                )


                tickets = extract_field(
                    decision_text,
                    "RELEVANT TICKETS",
                )


                reason = extract_field(
                    decision_text,
                    "REASON",
                )


                next_action = extract_field(
                    decision_text,
                    "NEXT ACTION",
                )


                missing = extract_field(
                    decision_text,
                    "MISSING INFORMATION",
                )


                # ------------------------------------------------
                # DECISION
                # ------------------------------------------------

                st.info(
                    f"Decision: **{decision}**"
                )


                # ------------------------------------------------
                # METADATA
                # ------------------------------------------------

                meta1, meta2, meta3 = st.columns(
                    3
                )


                with meta1:

                    st.caption(
                        "CATEGORY"
                    )

                    st.write(
                        category
                    )


                with meta2:

                    st.caption(
                        "POLICIES"
                    )

                    st.write(
                        policies
                    )


                with meta3:

                    st.caption(
                        "TICKETS"
                    )

                    st.write(
                        tickets
                    )


                # ------------------------------------------------
                # REASONING
                # ------------------------------------------------

                with st.expander(
                    "View reasoning & routing details"
                ):

                    st.markdown(
                        "**Reason**"
                    )

                    st.write(
                        reason
                    )


                    st.markdown(
                        "**Next action**"
                    )

                    st.write(
                        next_action
                    )


                    st.markdown(
                        "**Missing information**"
                    )

                    st.write(
                        missing
                    )


                    st.markdown(
                        "**Relevant policies**"
                    )

                    st.write(
                        policies
                    )


                    st.markdown(
                        "**Relevant historical tickets**"
                    )

                    st.write(
                        tickets
                    )


# ============================================================
# PROCESS QUICK REQUEST
# ============================================================

if st.session_state.pending_prompt:

    prompt = (
        st.session_state.pending_prompt
    )


    st.session_state.pending_prompt = None


    # --------------------------------------------------------
    # SAVE USER MESSAGE
    # --------------------------------------------------------

    current_chat["messages"].append(
        {
            "role": "user",
            "content": prompt,
        }
    )


    # --------------------------------------------------------
    # SET CHAT TITLE
    # --------------------------------------------------------

    if (
        current_chat["title"]
        == "New conversation"
    ):

        title = prompt.strip()


        if len(title) > 32:

            title = (
                title[:32]
                + "..."
            )


        current_chat["title"] = (
            title
        )


    # --------------------------------------------------------
    # RUN AGENT
    # --------------------------------------------------------

    with st.spinner(
        "◈  Veridian Agent is analyzing..."
    ):

        result = run_agent(
            prompt,
            thread_id=current_chat[
                "thread_id"
            ],
        )


    # --------------------------------------------------------
    # SAVE ASSISTANT MESSAGE
    # --------------------------------------------------------

    current_chat["messages"].append(
        {
            "role": "assistant",
            "content": result["response"],
            "decision": result["decision"],
        }
    )


    current_chat["request_count"] += 1


    st.rerun()


# ============================================================
# CHAT INPUT
# ============================================================

user_prompt = st.chat_input(
    "Describe your IT issue or request..."
)


if user_prompt:

    # --------------------------------------------------------
    # SAVE USER MESSAGE
    # --------------------------------------------------------

    current_chat["messages"].append(
        {
            "role": "user",
            "content": user_prompt,
        }
    )


    # --------------------------------------------------------
    # SET CHAT TITLE
    # --------------------------------------------------------

    if (
        current_chat["title"]
        == "New conversation"
    ):

        title = user_prompt.strip()


        if len(title) > 32:

            title = (
                title[:32]
                + "..."
            )


        current_chat["title"] = (
            title
        )


    # --------------------------------------------------------
    # RUN AGENT
    # --------------------------------------------------------

    with st.spinner(
        "◈  Veridian Agent is analyzing..."
    ):

        result = run_agent(
            user_prompt,
            thread_id=current_chat[
                "thread_id"
            ],
        )


    # --------------------------------------------------------
    # SAVE ASSISTANT RESPONSE
    # --------------------------------------------------------

    current_chat["messages"].append(
        {
            "role": "assistant",
            "content": result["response"],
            "decision": result["decision"],
        }
    )


    current_chat["request_count"] += 1


    st.rerun()