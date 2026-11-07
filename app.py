import streamlit as st
import base64

from datetime import datetime, date, timedelta
from io import BytesIO
from pathlib import Path

from PIL import Image

from ai_model import (
    understand_request,
    apply_user_date_rules,
    apply_user_time_rules,
    resolve_date_expression
)

from database import (
    get_teachers,
    get_teacher_schedule,
    get_available_classrooms,
    add_teacher_leave,
    cancel_teacher_leave,
    get_leave_records,
    book_makeup_class,
    is_teacher_on_leave
)


# --------------------------------------------------
# PATHS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

LOGO_PATH = BASE_DIR / "college_logo.png"
BACKGROUND_PATH = BASE_DIR / "campus.jpeg"
USER_ICON_PATH = BASE_DIR / "user_icon.png"
ASSISTANT_ICON_PATH = BASE_DIR / "assistant_icon.png"


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Kinnaird Campus Assistant",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "🏫",
    layout="centered",
    initial_sidebar_state="expanded"
)


# --------------------------------------------------
# IMAGE FUNCTIONS
# --------------------------------------------------

def load_image(path):
    if not path.exists():
        return None
    try:
        return Image.open(path)
    except Exception:
        return None


def image_base64(path):
    if not path.exists():
        return None
    try:
        with open(path, "rb") as file:
            return base64.b64encode(file.read()).decode()
    except Exception:
        return None


def pil_image_to_base64(image):
    if image is None:
        return None
    try:
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()
    except Exception:
        return None


def remove_logo_background(image):
    if image is None:
        return None
    try:
        image = image.convert("RGBA")
        pixels = image.load()
        width, height = image.size

        for y in range(height):
            for x in range(width):
                r, g, b, a = pixels[x, y]
                if r > 235 and g > 235 and b > 235:
                    pixels[x, y] = (r, g, b, 0)

        return image
    except Exception:
        return image


college_logo = load_image(LOGO_PATH)
college_logo_transparent = remove_logo_background(college_logo)
user_icon = load_image(USER_ICON_PATH)
assistant_icon = load_image(ASSISTANT_ICON_PATH)
background_encoded = image_base64(BACKGROUND_PATH)


def avatar_for(role):
    if role == "user":
        return user_icon if user_icon is not None else "👤"
    return assistant_icon if assistant_icon is not None else "🤖"


# --------------------------------------------------
# BACKGROUND
# --------------------------------------------------

if background_encoded:

    background_css = f"""
    .stApp {{
        background-image:
            linear-gradient(
                rgba(0,0,0,0.16),
                rgba(0,0,0,0.16)
            ),
            url("data:image/jpeg;base64,{background_encoded}");

        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: scroll;
        min-height: 100vh;
    }}
    """

else:

    background_css = """
    .stApp {
        background: #17251b !important;
    }
    """


# --------------------------------------------------
# CSS  (glass look)
# --------------------------------------------------

APP_CSS = """

/* ===================== GLASS TOKENS ===================== */

:root {
    --glass-bg:
        linear-gradient(135deg, rgba(255,255,255,0.16), rgba(255,255,255,0.04)),
        rgba(8, 14, 18, 0.42);

    --glass-bg-user:
        linear-gradient(135deg, rgba(255,226,196,0.20), rgba(255,226,196,0.05)),
        rgba(46, 28, 20, 0.46);

    --glass-bg-strong:
        linear-gradient(135deg, rgba(255,255,255,0.12), rgba(255,255,255,0.03)),
        rgba(6, 10, 14, 0.58);

    --glass-input-bg: rgba(3, 6, 9, 0.78);

    --glass-border: 1px solid rgba(255, 255, 255, 0.30);

    --glass-shadow:
        0 8px 32px rgba(0, 0, 0, 0.38),
        inset 0 1px 0 rgba(255, 255, 255, 0.28);

    --glass-blur: blur(16px) saturate(150%);
}


/* ===================== BASE ===================== */

[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main,
.main {
    background: transparent !important;
}

.block-container {
    max-width: 950px !important;
    padding-top: 120px !important;
    padding-bottom: 150px !important;
    background: transparent !important;
}

/* Keep Streamlit's header (it holds the sidebar open/close
   arrow) but make it invisible. */
header[data-testid="stHeader"] {
    background: transparent !important;
    position: relative !important;
    z-index: 10020 !important;
    pointer-events: auto !important;
}

/* Never hide Streamlit's native sidebar toggle. */
header[data-testid="stHeader"] button,
header[data-testid="stHeader"] button svg,
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stExpandSidebarButton"],
[data-testid="stExpandSidebarButton"] button {
    color: #ffffff !important;
    fill: #ffffff !important;
    opacity: 1 !important;
    visibility: visible !important;
    pointer-events: auto !important;
}

[data-testid="stDecoration"],
footer {
    display: none !important;
}

hr {
    border-color: rgba(255,255,255,0.28) !important;
}


/* ===================== TOP HEADER ===================== */

.top-header-background {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    width: 100vw;
    height: 105px;
    background:
        linear-gradient(180deg, rgba(255,255,255,0.10), rgba(255,255,255,0.02)),
        rgba(7, 12, 10, 0.50);
    backdrop-filter: blur(18px) saturate(140%);
    -webkit-backdrop-filter: blur(18px) saturate(140%);
    border-bottom: 1px solid rgba(255,255,255,0.25);
    box-shadow: 0 6px 24px rgba(0,0,0,0.35);
    z-index: 9990;
    pointer-events: none;
}

.custom-header-content {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 105px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    z-index: 9999;
    pointer-events: none;
}

.header-logo-holder {
    width: 92px;
    height: 90px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

.header-logo-holder img {
    max-width: 96px;
    max-height: 94px;
    object-fit: contain;
}

.campus-title {
    color: #fff7df !important;
    font-family: TypeSETit, "Great Vibes", serif;
    font-size: 30px;
    font-weight: 800;
    line-height: 1.1;
    white-space: nowrap;
    text-shadow: 2px 2px 0 #000, 0 4px 10px rgba(0,0,0,0.95);
}


/* ===================== SIDEBAR ===================== */

section[data-testid="stSidebar"] {
    background: var(--glass-bg-strong) !important;
    backdrop-filter: blur(20px) saturate(150%);
    -webkit-backdrop-filter: blur(20px) saturate(150%);
    border-right: 1px solid rgba(255,255,255,0.25) !important;
    box-shadow: 8px 0 32px rgba(0,0,0,0.35);
}

section[data-testid="stSidebar"] > div {
    background: transparent !important;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label {
    color: #ffffff !important;
}


/* ===================== CHAT BUBBLES ===================== */

div[data-testid="stChatMessage"] {
    border-radius: 20px !important;
    padding: 13px 18px !important;
    margin-top: 10px !important;
    margin-bottom: 10px !important;
    background: var(--glass-bg) !important;
    border: var(--glass-border) !important;
    box-shadow: var(--glass-shadow) !important;
    backdrop-filter: var(--glass-blur);
    -webkit-backdrop-filter: var(--glass-blur);
}

div[data-testid="stChatMessage"]:has(
    div[data-testid="stChatMessageAvatarUser"]
) {
    background: var(--glass-bg-user) !important;
    border: 1px solid rgba(255,226,196,0.38) !important;
}

div[data-testid="stChatMessage"]:has(
    div[data-testid="stChatMessageAvatarAssistant"]
) {
    background: var(--glass-bg) !important;
}

div[data-testid="stChatMessage"] > div,
div[data-testid="stChatMessage"] > div > div,
div[data-testid="stChatMessage"] > div > div > div {
    background: transparent !important;
    border: none !important;
}


/* ===================== TEXT ===================== */

div[data-testid="stChatMessage"] p,
div[data-testid="stChatMessage"] span,
div[data-testid="stChatMessage"] li,
div[data-testid="stChatMessage"] ol,
div[data-testid="stChatMessage"] ul {
    color: #ffffff !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    line-height: 1.55 !important;
}

div[data-testid="stChatMessage"] strong {
    color: #ffffff !important;
    font-weight: 800 !important;
}

div[data-testid="stChatMessage"] h1,
div[data-testid="stChatMessage"] h2,
div[data-testid="stChatMessage"] h3,
div[data-testid="stChatMessage"] h4 {
    color: #ffffff !important;
    text-shadow: 0 2px 8px rgba(0,0,0,0.5);
}


/* ===================== TABLES (inside chat bubbles) ===================== */

div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
    overflow-x: auto;
}

div[data-testid="stChatMessage"] table {
    width: 100%;
    border-collapse: separate !important;
    border-spacing: 0 !important;
    border: 1px solid rgba(255,255,255,0.30) !important;
    border-radius: 14px !important;
    overflow: hidden;
    background: rgba(255,255,255,0.04) !important;
    margin: 6px 0 4px 0;
}

div[data-testid="stChatMessage"] th {
    background: rgba(255,255,255,0.16) !important;
    color: #ffffff !important;
    font-size: 14px !important;
    font-weight: 800 !important;
    text-align: left !important;
    padding: 9px 12px !important;
    border: none !important;
    border-bottom: 1px solid rgba(255,255,255,0.28) !important;
    white-space: nowrap;
}

div[data-testid="stChatMessage"] td {
    color: #ffffff !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    padding: 8px 12px !important;
    border: none !important;
    border-top: 1px solid rgba(255,255,255,0.12) !important;
    background: transparent !important;
}

div[data-testid="stChatMessage"] tr:hover td {
    background: rgba(255,255,255,0.07) !important;
}


/* ===================== AVATARS ===================== */

div[data-testid="stChatMessageAvatarUser"],
div[data-testid="stChatMessageAvatarAssistant"] {
    background: transparent !important;
    width: 40px !important;
    height: 40px !important;
    min-width: 40px !important;
}

div[data-testid="stChatMessageAvatarUser"] img,
div[data-testid="stChatMessageAvatarAssistant"] img {
    width: 38px !important;
    height: 38px !important;
    min-width: 38px !important;
    min-height: 38px !important;
    object-fit: cover !important;
    border-radius: 50% !important;
    box-shadow: 0 0 0 2px rgba(255,255,255,0.35);
}


/* ===================== PANELS (flows + confirmation) ===================== */

.st-key-flow_panel,
.st-key-confirm_panel {
    background: var(--glass-bg) !important;
    border: var(--glass-border) !important;
    border-radius: 20px !important;
    padding: 16px 20px !important;
    margin-top: 12px !important;
    box-shadow: var(--glass-shadow) !important;
    backdrop-filter: var(--glass-blur);
    -webkit-backdrop-filter: var(--glass-blur);
}

.st-key-flow_panel h1, .st-key-flow_panel h2, .st-key-flow_panel h3,
.st-key-confirm_panel h1, .st-key-confirm_panel h2, .st-key-confirm_panel h3,
.st-key-flow_panel p, .st-key-flow_panel li, .st-key-flow_panel span,
.st-key-confirm_panel p, .st-key-confirm_panel li, .st-key-confirm_panel span,
.st-key-flow_panel label, .st-key-confirm_panel label {
    color: #ffffff !important;
}

.st-key-flow_panel h3,
.st-key-confirm_panel h3 {
    text-shadow: 0 2px 8px rgba(0,0,0,0.5);
}

[data-testid="stForm"] {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.28) !important;
    border-radius: 16px !important;
}

div[data-testid="stAlert"] {
    background:
        linear-gradient(135deg, rgba(255,255,255,0.12), rgba(255,255,255,0.03)),
        rgba(5, 8, 10, 0.50) !important;
    border: 1px solid rgba(255,255,255,0.32) !important;
    border-radius: 16px !important;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
}

div[data-testid="stAlert"] * {
    color: #ffffff !important;
}


/* ===================== INPUTS (inside panels) ===================== */

div[data-baseweb="input"],
div[data-baseweb="base-input"] {
    background: rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
}

div[data-baseweb="input"] {
    border: 1px solid rgba(255,255,255,0.40) !important;
}

div[data-baseweb="input"] input {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    background: transparent !important;
}

div[data-baseweb="input"] input::placeholder {
    color: rgba(255,255,255,0.55) !important;
    -webkit-text-fill-color: rgba(255,255,255,0.55) !important;
}


/* ===================== BUTTONS ===================== */

div.stButton > button,
[data-testid="stFormSubmitButton"] button {
    background:
        linear-gradient(135deg, rgba(255,255,255,0.24), rgba(255,255,255,0.07)) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255,255,255,0.42) !important;
    border-radius: 14px !important;
    font-weight: 700 !important;
    box-shadow:
        0 4px 14px rgba(0,0,0,0.28),
        inset 0 1px 0 rgba(255,255,255,0.30) !important;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    transition: background 0.18s ease, transform 0.18s ease, border-color 0.18s ease;
}

div.stButton > button p,
[data-testid="stFormSubmitButton"] button p {
    color: #ffffff !important;
}

div.stButton > button:hover,
[data-testid="stFormSubmitButton"] button:hover {
    background:
        linear-gradient(135deg, rgba(255,255,255,0.38), rgba(255,255,255,0.14)) !important;
    border-color: #ffffff !important;
    transform: translateY(-1px);
}

div.stButton > button:active,
[data-testid="stFormSubmitButton"] button:active {
    transform: translateY(0);
}


/* ===================== SEARCHING ===================== */

.searching-container {
    display: flex;
    align-items: center;
    gap: 10px;
    color: white;
    font-size: 16px;
    font-weight: 700;
}

.searching-text {
    color: white !important;
}

.ai-searching-dots {
    display: flex;
    gap: 5px;
}

.ai-searching-dots span {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: white;
    animation: searchingDots 1.2s infinite ease-in-out;
}

.ai-searching-dots span:nth-child(1) { animation-delay: 0s; }
.ai-searching-dots span:nth-child(2) { animation-delay: 0.18s; }
.ai-searching-dots span:nth-child(3) { animation-delay: 0.36s; }

@keyframes searchingDots {
    0%, 100% { opacity: 0.25; transform: translateY(0); }
    25%      { opacity: 1;    transform: translateY(-4px); }
    50%      { opacity: 0.35; transform: translateY(0); }
}


/* ===================== CHAT INPUT ===================== */

/* 1. Remove the black bar behind the input: make everything in
      the bottom area transparent (including pseudo-elements). */
[data-testid="stBottom"],
[data-testid="stBottom"] *,
[data-testid="stBottom"]::before,
[data-testid="stBottom"]::after,
[data-testid="stBottom"] *::before,
[data-testid="stBottom"] *::after,
[data-testid="stBottomBlockContainer"] {
    background: transparent !important;
    background-color: transparent !important;
    background-image: none !important;
    box-shadow: none !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
}

/* 2. Lift the input a little off the bottom edge. */
[data-testid="stBottomBlockContainer"] {
    max-width: 950px !important;
    margin: auto !important;
    padding-bottom: 62px !important;
}

/* 3. Only the input box itself is drawn: dark glass, a little
      darker than the chat bubbles. */
[data-testid="stBottom"] [data-testid="stChatInput"] {
    background: var(--glass-input-bg) !important;
    border: 1px solid rgba(255,255,255,0.38) !important;
    border-radius: 18px !important;
    padding: 2px 4px !important;
    box-shadow:
        0 10px 30px rgba(0,0,0,0.45),
        inset 0 1px 0 rgba(255,255,255,0.18) !important;
    backdrop-filter: blur(16px) saturate(150%) !important;
    -webkit-backdrop-filter: blur(16px) saturate(150%) !important;
}

[data-testid="stBottom"] [data-testid="stChatInput"] > div {
    border: none !important;
    outline: none !important;
}

div[data-testid="stChatInput"] textarea {
    color: #ffffff !important;
    caret-color: #ffffff !important;
    font-size: 16px !important;
    font-weight: 600 !important;
}

div[data-testid="stChatInput"] textarea::placeholder {
    color: rgba(255,255,255,0.70) !important;
    opacity: 0.6 !important;
}

div[data-testid="stChatInput"] button {
    color: #ffffff !important;
}


/* ===================== MOBILE ===================== */

@media (max-width: 700px) {

    .block-container {
        padding-top: 105px !important;
        padding-left: 0.65rem !important;
        padding-right: 0.65rem !important;
        padding-bottom: 130px !important;
    }

    [data-testid="stBottomBlockContainer"] {
        padding-bottom: 24px !important;
    }

    .top-header-background {
        height: 88px;
    }

    .custom-header-content {
        height: 88px;
        gap: 6px;
    }

    .header-logo-holder {
        width: 74px;
        height: 74px;
    }

    .header-logo-holder img {
        max-width: 70px;
        max-height: 70px;
    }

    .campus-title {
        font-size: 22px;
        white-space: normal;
        text-align: center;
    }

    div[data-testid="stChatMessage"] {
        padding: 10px 14px !important;
        border-radius: 16px !important;
    }

    div[data-testid="stChatMessage"] p,
    div[data-testid="stChatMessage"] span,
    div[data-testid="stChatMessage"] li {
        font-size: 15px !important;
    }
}
"""

st.markdown(
    "<style>" + background_css + APP_CSS + "</style>",
    unsafe_allow_html=True
)


# --------------------------------------------------
# HEADER
# --------------------------------------------------

logo_b64 = pil_image_to_base64(college_logo_transparent)

if logo_b64:
    logo_html = (
        '<div class="header-logo-holder">'
        f'<img src="data:image/png;base64,{logo_b64}">'
        '</div>'
    )
else:
    logo_html = ""

st.markdown(
    '<div class="top-header-background"></div>'
    '<div class="custom-header-content">'
    + logo_html +
    '<div class="campus-title">Kinnaird Campus Assistant</div>'
    '</div>',
    unsafe_allow_html=True
)


# --------------------------------------------------
# CONSTANTS
# --------------------------------------------------

# (label shown on button, start_time, end_time)  -- times in 24h "HH:MM"
TIME_SLOTS = [
    ("8:00 – 9:00",    "08:00", "09:00"),
    ("9:00 – 10:00",   "09:00", "10:00"),
    ("10:00 – 11:00",  "10:00", "11:00"),
    ("11:00 – 12:00",  "11:00", "12:00"),
    ("12:00 – 1:00",   "12:00", "13:00"),
    ("1:30 – 2:30",    "13:30", "14:30"),
    ("2:30 – 3:30",    "14:30", "15:30"),
    ("3:30 – 4:30",    "15:30", "16:30"),
]

SEARCHING_HTML = (
    '<div class="searching-container">'
    '<span class="searching-text">🔎 Searching...</span>'
    '<div class="ai-searching-dots">'
    '<span></span><span></span><span></span>'
    '</div>'
    '</div>'
)


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_action" not in st.session_state:
    st.session_state.pending_action = None

# Guided flow started from a sidebar button (None when idle)
if "flow" not in st.session_state:
    st.session_state.flow = None


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def find_teacher(teacher_name):
    teachers = get_teachers()

    for teacher in teachers:
        if teacher_name.lower().strip() == teacher["teacher_name"].lower().strip():
            return teacher["teacher_id"]

    for teacher in teachers:
        if teacher_name.lower().strip() == teacher["teacher_id"].lower().strip():
            return teacher["teacher_id"]

    return None


def get_teacher_display_name(teacher_id, fallback=""):
    for teacher in get_teachers():
        if teacher["teacher_id"] == teacher_id:
            return teacher["teacher_name"]
    return fallback


def process_user_request(user_message):
    ai_result = understand_request(user_message)

    ai_result = apply_user_date_rules(ai_result, user_message)
    ai_result = apply_user_time_rules(ai_result, user_message)

    return ai_result


def get_resolved_date(ai_result):
    date_expression = ai_result.get("date_expression")

    if date_expression:
        return resolve_date_expression(date_expression)

    return None


def get_resolved_leave_dates(ai_result):
    start_expression = ai_result.get("start_date_expression")
    end_expression = ai_result.get("end_date_expression")

    if start_expression:
        start_date = resolve_date_expression(start_expression)
    else:
        start_date = get_resolved_date(ai_result)

    if end_expression:
        end_date = resolve_date_expression(end_expression)
    else:
        end_date = start_date

    return start_date, end_date


def add_assistant_message(message):
    st.session_state.messages.append({
        "role": "assistant",
        "content": message
    })


def normalize_time(value):
    """Turn '8:00', '08:00:00', datetime.time etc. into 'HH:MM'."""
    parts = str(value).strip().split(":")
    return f"{int(parts[0]):02d}:{parts[1][:2]}"


def times_overlap(start_a, end_a, start_b, end_b):
    start_a, end_a = normalize_time(start_a), normalize_time(end_a)
    start_b, end_b = normalize_time(start_b), normalize_time(end_b)
    return start_a < end_b and end_a > start_b


def check_teacher_availability(teacher_id, date_value, start_time, end_time):
    """Return (is_free, reason). reason explains why the teacher is not free."""
    if is_teacher_on_leave(teacher_id, date_value):
        return False, "is on leave on this date"

    schedule = get_teacher_schedule(teacher_id, date_value) or []

    for entry in schedule:
        if entry.get("status") != "OCCUPIED":
            continue

        if times_overlap(
            start_time, end_time,
            entry.get("start_time", "00:00"),
            entry.get("end_time", "00:00")
        ):
            return False, (
                f"already has a {entry.get('class_type', '').lower()} class "
                f"({entry.get('start_time')} - {entry.get('end_time')}) at that time"
            )

    return True, ""


# --------------------------------------------------
# TIMETABLE TABLES
# --------------------------------------------------

def entry_cells(entry):
    """Turn one timetable entry into (time, room, type, status) table cells."""
    start = entry.get("start_time", "")
    end = entry.get("end_time", "")
    room = entry.get("classroom_id", "")

    if str(entry.get("class_type", "")).lower() == "makeup":
        type_label = "🔁 **Makeup**"
    else:
        type_label = "Regular"

    status = str(entry.get("status", ""))

    if "LEAVE" in status.upper():
        status_label = "🟢 Free (teacher on leave)"
    elif status.upper() == "OCCUPIED":
        status_label = "🔴 Occupied"
    else:
        status_label = status

    return f"{start} – {end}", str(room), type_label, status_label


def format_schedule(teacher_name, date_value, schedule):
    """One day's timetable as a table (used for manual chat questions)."""
    try:
        day_name = datetime.strptime(str(date_value), "%Y-%m-%d").strftime("%A")
        date_label = f"{day_name}, {date_value}"
    except ValueError:
        date_label = str(date_value)

    if not schedule:
        return (
            f"No timetable entries were found for "
            f"**{teacher_name}** on **{date_label}**."
        )

    result = f"### Timetable for {teacher_name}\n"
    result += f"**Date:** {date_label}\n\n"
    result += "| Time | Room | Type | Status |\n"
    result += "|---|---|---|---|\n"

    for entry in schedule:
        time_cell, room, type_label, status_label = entry_cells(entry)
        result += f"| {time_cell} | {room} | {type_label} | {status_label} |\n"

    return result


def get_week_monday():
    """Monday of the current week (the coming Monday if today is a weekend)."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    if today.weekday() >= 5:
        monday += timedelta(days=7)

    return monday


def format_week_schedule(teacher_name, teacher_id):
    """Monday-Friday timetable as one table (used by the quick action)."""
    monday = get_week_monday()
    friday = monday + timedelta(days=4)
    today = date.today()

    result = f"### Weekly timetable for {teacher_name}\n"
    result += (
        f"**Week:** {monday.strftime('%d %b')} – "
        f"{friday.strftime('%d %b %Y')}\n\n"
    )
    result += "| Day | Time | Room | Type | Status |\n"
    result += "|---|---|---|---|---|\n"

    for offset in range(5):
        day = monday + timedelta(days=offset)
        schedule = get_teacher_schedule(teacher_id, day.isoformat()) or []

        day_label = f"**{day.strftime('%a %d %b')}**"
        if day == today:
            day_label += " (today)"

        if not schedule:
            result += f"| {day_label} | — | — | — | No classes |\n"
            continue

        for index, entry in enumerate(schedule):
            time_cell, room, type_label, status_label = entry_cells(entry)
            label = day_label if index == 0 else ""
            result += (
                f"| {label} | {time_cell} | {room} | "
                f"{type_label} | {status_label} |\n"
            )

    return result


# --------------------------------------------------
# QUERY HANDLER
# --------------------------------------------------

def execute_query(ai_result):

    operation = ai_result.get("operation")

    # TEACHER TIMETABLE
    if operation == "check_teacher_schedule":

        teacher_name = ai_result.get("teacher_name", "")
        teacher_id = find_teacher(teacher_name)

        if not teacher_id:
            return f"I couldn't find the teacher '{teacher_name}' in the database."

        date_value = get_resolved_date(ai_result)

        if not date_value:
            return "I couldn't understand the requested date."

        schedule = get_teacher_schedule(teacher_id, date_value)

        return format_schedule(teacher_name, date_value, schedule)

    # CLASSROOM AVAILABILITY
    elif operation == "check_classroom_availability":

        date_value = get_resolved_date(ai_result)

        start_time = ai_result.get("start_time")
        end_time = ai_result.get("end_time")

        if not date_value:
            return "I couldn't understand the requested date."

        if not start_time or not end_time:
            return "Please specify the time for classroom availability."

        available_rooms = get_available_classrooms(
            date_value,
            start_time,
            end_time
        )

        if not available_rooms:
            return (
                f"No classrooms are available on {date_value} "
                f"from {start_time} to {end_time}."
            )

        result = (
            f"### Available Classrooms\n"
            f"**Date:** {date_value}\n"
            f"**Time:** {start_time} - {end_time}\n\n"
        )

        for room in available_rooms:
            result += f"- {room}\n"

        result += f"\n**Total available:** {len(available_rooms)}"

        return result

    return "I couldn't process this request."


# --------------------------------------------------
# PREPARE ACTIONS
# --------------------------------------------------

def prepare_action(ai_result):

    operation = ai_result.get("operation")

    # ADD LEAVE
    if operation == "add_leave":

        teacher_name = ai_result.get("teacher_name", "")
        teacher_id = find_teacher(teacher_name)

        if not teacher_id:
            return None, f"Teacher '{teacher_name}' was not found."

        start_date, end_date = get_resolved_leave_dates(ai_result)

        if not start_date or not end_date:
            return None, "I couldn't understand the leave dates."

        if start_date > end_date:
            return None, "The end date cannot be before the start date."

        action = {
            "operation": "add_leave",
            "teacher_id": teacher_id,
            "teacher_name": teacher_name,
            "start_date": start_date,
            "end_date": end_date
        }

        message = (
            f"Please confirm the following leave:\n\n"
            f"- **Teacher:** {teacher_name}\n"
            f"- **From:** {start_date}\n"
            f"- **To:** {end_date}\n\n"
            f"Do you want to approve this leave?"
        )

        return action, message

    # CANCEL LEAVE
    elif operation == "cancel_leave":

        leave_id = ai_result.get("leave_id")

        if leave_id is None:
            return None, "Please provide the leave record ID to cancel."

        leave_records = get_leave_records()

        selected_record = None

        for record in leave_records:
            if record["leave_id"] == int(leave_id):
                selected_record = record
                break

        if not selected_record:
            return None, f"Leave record {leave_id} was not found."

        action = {
            "operation": "cancel_leave",
            "leave_id": int(leave_id),
            "teacher_name": selected_record["teacher_name"],
            "start_date": selected_record["start_date"],
            "end_date": selected_record["end_date"]
        }

        message = (
            f"Please confirm cancellation of this leave:\n\n"
            f"- **Leave ID:** {leave_id}\n"
            f"- **Teacher:** {selected_record['teacher_name']}\n"
            f"- **From:** {selected_record['start_date']}\n"
            f"- **To:** {selected_record['end_date']}\n\n"
            f"Do you want to cancel this leave?"
        )

        return action, message

    return None, "This action could not be prepared."


# --------------------------------------------------
# GUIDED FLOWS (started from the sidebar buttons)
# --------------------------------------------------

def end_flow():
    st.session_state.flow = None
    st.rerun()


def flow_add_leave():
    st.subheader("📝 Add a Leave")

    with st.form("add_leave_form"):
        teacher_name = st.text_input("Teacher name or ID")

        # No pre-selected date: the user picks one day, or a start
        # and an end date for several days.
        leave_dates = st.date_input(
            "Leave date (click one day, or click a start and an end date for multiple days)",
            value=()
        )

        submitted = st.form_submit_button("Continue")

    if st.button("Back", key="leave_back"):
        end_flow()

    if not submitted:
        return

    teacher_id = find_teacher(teacher_name) if teacher_name.strip() else None

    if not teacher_id:
        st.error(f"Teacher '{teacher_name}' was not found.")
        return

    # date_input returns nothing, a date, or a tuple of 0-2 dates
    if not leave_dates:
        st.error("Please pick a leave date.")
        return

    if isinstance(leave_dates, (tuple, list)):
        start = leave_dates[0]
        end = leave_dates[-1]
    else:
        start = end = leave_dates

    if start > end:
        st.error("The end date cannot be before the start date.")
        return

    teacher_display = get_teacher_display_name(teacher_id, teacher_name)

    st.session_state.pending_action = {
        "operation": "add_leave",
        "teacher_id": teacher_id,
        "teacher_name": teacher_display,
        "start_date": start.isoformat(),
        "end_date": end.isoformat()
    }

    add_assistant_message(
        f"Please confirm the following leave:\n\n"
        f"- **Teacher:** {teacher_display}\n"
        f"- **From:** {start.isoformat()}\n"
        f"- **To:** {end.isoformat()}\n\n"
        f"Use the confirmation panel below to approve or cancel."
    )

    end_flow()


def flow_remove_leave():
    st.subheader("🗑️ Remove a Leave")

    today = date.today().isoformat()

    # Only leaves that are ongoing or still to come - nothing that
    # has already finished.
    records = [
        record for record in get_leave_records()
        if str(record["end_date"]) >= today
    ]

    records.sort(key=lambda record: (str(record["start_date"]), record["leave_id"]))

    if not records:
        st.info("There are no current or upcoming leaves to remove.")
    else:
        st.write("**Select the leave you want to cancel**")

        for record in records:
            start = str(record["start_date"])
            end = str(record["end_date"])

            if start == end:
                period = start
            else:
                period = f"{start} → {end}"

            if start <= today <= end:
                period += "  (ongoing)"

            info_col, button_col = st.columns([4, 1])

            info_col.markdown(
                f"**{record['teacher_name']}** — {period}  \n"
                f"Leave ID: {record['leave_id']}"
            )

            if button_col.button(
                "Remove",
                key=f"remove_leave_{record['leave_id']}",
                width="stretch"
            ):
                st.session_state.pending_action = {
                    "operation": "cancel_leave",
                    "leave_id": int(record["leave_id"]),
                    "teacher_name": record["teacher_name"],
                    "start_date": start,
                    "end_date": end
                }

                add_assistant_message(
                    f"Please confirm cancellation of this leave:\n\n"
                    f"- **Leave ID:** {record['leave_id']}\n"
                    f"- **Teacher:** {record['teacher_name']}\n"
                    f"- **From:** {start}\n"
                    f"- **To:** {end}\n\n"
                    f"Use the confirmation panel below to approve or cancel."
                )

                end_flow()

    if st.button("Back", key="remove_leave_back"):
        end_flow()


def flow_check_timetable():
    st.subheader("📅 Check Timetable")

    with st.form("timetable_form"):
        teacher_name = st.text_input("Teacher name or ID")
        submitted = st.form_submit_button("Show weekly timetable")

    if st.button("Back", key="timetable_back"):
        end_flow()

    if not submitted:
        return

    teacher_id = find_teacher(teacher_name) if teacher_name.strip() else None

    if not teacher_id:
        st.error(f"Teacher '{teacher_name}' was not found.")
        return

    teacher_display = get_teacher_display_name(teacher_id, teacher_name)

    add_assistant_message(format_week_schedule(teacher_display, teacher_id))

    end_flow()


def flow_book_classroom():
    flow = st.session_state.flow
    step = flow["step"]

    st.subheader("🏫 Book a Classroom")

    # Show what has been chosen so far
    chosen = []
    if flow.get("date"):
        chosen.append(f"**Day:** {flow['date']}")
    if flow.get("slot_label"):
        chosen.append(f"**Slot:** {flow['slot_label']}")
    if flow.get("teacher_name"):
        chosen.append(f"**Teacher:** {flow['teacher_name']}")
    if chosen:
        st.markdown("  |  ".join(chosen))

    # ---- STEP 1: DAY ----
    if step == "day":
        st.write("**Choose a day**")

        days = [date.today() + timedelta(days=i) for i in range(7)]
        cols = st.columns(len(days))

        for col, day in zip(cols, days):
            label = day.strftime("%a\n%d %b")
            if col.button(label, key=f"day_{day.isoformat()}", width="stretch"):
                flow["date"] = day.isoformat()
                flow["step"] = "slot"
                st.rerun()

    # ---- STEP 2: TIME SLOT ----
    elif step == "slot":
        st.write("**Choose a time slot**")

        cols = st.columns(4)

        for i, (label, start, end) in enumerate(TIME_SLOTS):
            if cols[i % 4].button(label, key=f"slot_{start}", width="stretch"):
                flow["slot_label"] = label
                flow["start_time"] = start
                flow["end_time"] = end
                flow["step"] = "teacher"
                st.rerun()

    # ---- STEP 3: TEACHER (typed) ----
    elif step == "teacher":
        with st.form("book_teacher_form"):
            teacher_name = st.text_input("Teacher name or ID")
            submitted = st.form_submit_button("Check availability")

        if submitted:
            teacher_id = find_teacher(teacher_name) if teacher_name.strip() else None

            if not teacher_id:
                st.error(f"Teacher '{teacher_name}' was not found.")
            else:
                teacher_display = get_teacher_display_name(teacher_id, teacher_name)

                is_free, reason = check_teacher_availability(
                    teacher_id, flow["date"],
                    flow["start_time"], flow["end_time"]
                )

                if not is_free:
                    st.error(
                        f"{teacher_display} {reason}. "
                        f"Try another teacher, or use Start over to choose a different day or slot."
                    )
                else:
                    flow["teacher_id"] = teacher_id
                    flow["teacher_name"] = teacher_display
                    flow["step"] = "room"
                    st.rerun()

    # ---- STEP 4: ROOM ----
    elif step == "room":
        st.success(f"{flow['teacher_name']} is available for this slot.")
        st.write("**Choose a room**")

        rooms = get_available_classrooms(
            flow["date"], flow["start_time"], flow["end_time"]
        )

        if not rooms:
            st.warning("No classrooms are free in this slot. Please pick a different slot.")
        else:
            cols = st.columns(4)

            for i, room in enumerate(rooms):
                if cols[i % 4].button(str(room), key=f"room_{room}", width="stretch"):
                    st.session_state.pending_action = {
                        "operation": "book_classroom",
                        "teacher_id": flow["teacher_id"],
                        "teacher_name": flow["teacher_name"],
                        "classroom_id": room,
                        "date": flow["date"],
                        "start_time": flow["start_time"],
                        "end_time": flow["end_time"],
                        "slot_label": flow["slot_label"]
                    }

                    add_assistant_message(
                        f"Please confirm this booking:\n\n"
                        f"- **Teacher:** {flow['teacher_name']}\n"
                        f"- **Room:** {room}\n"
                        f"- **Date:** {flow['date']}\n"
                        f"- **Time:** {flow['slot_label']}\n\n"
                        f"Use the confirmation panel below to approve or cancel."
                    )

                    end_flow()

    # ---- Navigation ----
    nav1, nav2 = st.columns(2)

    with nav1:
        if step != "day" and st.button("⬅ Start over", key="book_restart"):
            st.session_state.flow = {"type": "book_classroom", "step": "day"}
            st.rerun()

    with nav2:
        if st.button("Cancel booking", key="book_cancel"):
            end_flow()


def render_flow():
    flow = st.session_state.flow

    if not flow:
        return

    with st.container(border=True, key="flow_panel"):

        if flow["type"] == "add_leave":
            flow_add_leave()
        elif flow["type"] == "remove_leave":
            flow_remove_leave()
        elif flow["type"] == "check_timetable":
            flow_check_timetable()
        elif flow["type"] == "book_classroom":
            flow_book_classroom()


# --------------------------------------------------
# DISPLAY CHAT HISTORY
# --------------------------------------------------

for history_message in st.session_state.messages:

    with st.chat_message(
        history_message["role"],
        avatar=avatar_for(history_message["role"])
    ):
        st.markdown(history_message["content"])


# --------------------------------------------------
# USER INPUT
#
# The user's message appears straight away, then the assistant
# bubble shows "Searching..." and is overwritten by the result.
# --------------------------------------------------

user_message = st.chat_input("Ask something about classrooms or teachers...")

if user_message:

    # Typing in the chat box abandons any guided flow
    st.session_state.flow = None

    st.session_state.messages.append({
        "role": "user",
        "content": user_message
    })

    with st.chat_message("user", avatar=avatar_for("user")):
        st.markdown(user_message)

    with st.chat_message("assistant", avatar=avatar_for("assistant")):

        searching_placeholder = st.empty()
        searching_placeholder.markdown(
            SEARCHING_HTML,
            unsafe_allow_html=True
        )

        try:

            ai_result = process_user_request(user_message)

            operation = ai_result.get("operation")

            # READ-ONLY QUERY
            if operation in [
                "check_teacher_schedule",
                "check_classroom_availability"
            ]:

                response = execute_query(ai_result)

            # ACTION REQUIRING CONFIRMATION
            elif operation in ["add_leave", "cancel_leave"]:

                action, prepared_message = prepare_action(ai_result)

                if action:
                    st.session_state.pending_action = action

                response = prepared_message

            # UNKNOWN REQUEST
            else:

                response = (
                    "Sorry, I couldn't understand your request. "
                    "Try asking about a teacher's timetable, "
                    "classroom availability, or teacher leave."
                )

        except Exception as error:

            response = (
                f"Something went wrong while processing your request: {error}"
            )

        # Replace "Searching..." with the result
        searching_placeholder.markdown(response)

    add_assistant_message(response)


# --------------------------------------------------
# GUIDED FLOW PANEL
# --------------------------------------------------

render_flow()


# --------------------------------------------------
# CONFIRMATION PANEL
# --------------------------------------------------

if st.session_state.pending_action:

    with st.container(border=True, key="confirm_panel"):

        action = st.session_state.pending_action

        st.subheader("Confirm Action")

        operation = action["operation"]

        if operation == "add_leave":

            st.info(
                f"Record leave for **{action['teacher_name']}** "
                f"from **{action['start_date']}** "
                f"to **{action['end_date']}**?"
            )

        elif operation == "cancel_leave":

            st.warning(
                f"Cancel leave record **{action['leave_id']}** "
                f"for **{action['teacher_name']}** "
                f"({action['start_date']} → {action['end_date']})?"
            )

        elif operation == "book_classroom":

            st.info(
                f"Book room **{action['classroom_id']}** for "
                f"**{action['teacher_name']}** on **{action['date']}** "
                f"({action['slot_label']})?"
            )

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "Confirm",
                width="stretch"
            ):

                try:

                    if operation == "add_leave":

                        leave_id = add_teacher_leave(
                            action["teacher_id"],
                            action["start_date"],
                            action["end_date"]
                        )

                        success_message = (
                            f"### Leave Successfully Recorded! ✅\n\n"
                            f"- **Teacher:** {action['teacher_name']}\n"
                            f"- **Leave ID:** {leave_id}\n"
                            f"- **From:** {action['start_date']}\n"
                            f"- **To:** {action['end_date']}\n\n"
                            f"The leave has been saved to the database."
                        )

                    elif operation == "cancel_leave":

                        cancelled = cancel_teacher_leave(
                            action["leave_id"]
                        )

                        if cancelled:

                            success_message = (
                                f"### Leave Successfully Cancelled! ✅\n\n"
                                f"- **Leave ID:** {action['leave_id']}\n"
                                f"- **Teacher:** {action['teacher_name']}\n\n"
                                f"The leave record has been removed from the database."
                            )

                        else:

                            success_message = (
                                f"Leave record {action['leave_id']} "
                                f"could not be cancelled."
                            )

                    elif operation == "book_classroom":

                        book_makeup_class(
                            action["teacher_id"],
                            action["classroom_id"],
                            action["date"],
                            action["start_time"],
                            action["end_time"]
                        )

                        success_message = (
                            f"### Classroom Booked! ✅\n\n"
                            f"- **Teacher:** {action['teacher_name']}\n"
                            f"- **Room:** {action['classroom_id']}\n"
                            f"- **Date:** {action['date']}\n"
                            f"- **Time:** {action['slot_label']}\n\n"
                            f"The booking has been saved to the database."
                        )

                    add_assistant_message(success_message)

                    st.session_state.pending_action = None
                    st.rerun()

                except Exception as error:

                    st.error(f"Operation failed: {error}")

        with col2:

            if st.button(
                "Cancel",
                width="stretch"
            ):

                add_assistant_message(
                    "The operation was cancelled. No changes were made."
                )

                st.session_state.pending_action = None
                st.rerun()


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:

    st.header("Quick Actions")

    if st.button("📝 Add a Leave", width="stretch"):
        st.session_state.pending_action = None
        st.session_state.flow = {"type": "add_leave"}
        st.rerun()

    if st.button("🗑️ Remove a Leave", width="stretch"):
        st.session_state.pending_action = None
        st.session_state.flow = {"type": "remove_leave"}
        st.rerun()

    if st.button("📅 Check Timetable", width="stretch"):
        st.session_state.pending_action = None
        st.session_state.flow = {"type": "check_timetable"}
        st.rerun()

    if st.button("🏫 Book a Classroom", width="stretch"):
        st.session_state.pending_action = None
        st.session_state.flow = {"type": "book_classroom", "step": "day"}
        st.rerun()

    st.divider()

    if st.button("🧹 Clear Chat", width="stretch"):
        st.session_state.messages = []
        st.session_state.pending_action = None
        st.session_state.flow = None
        st.rerun()