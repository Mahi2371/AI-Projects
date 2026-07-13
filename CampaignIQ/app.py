"""
CampaignIQ — v1.0 (Production)
================================
A unified marketing intelligence hub for campaign data analysis.

Features:
  1. Multi-source ingestion — SA360, Google Ads, Meta Ads, DV360, GA4, Custom CSV
  2. Auto-detection of data source by column signature (no manual tagging)
  3. Dedicated SQLite tables per source — sa360_campaigns, gads_performance,
     meta_ads, dv360_display, ga4_analytics, custom_uploads, uploads_registry
  4. SQL-powered insight bot — LangChain SQL agent + SQLAlchemy + natural language
  5. Smart chart router — auto-picks bar/line/pie/scatter based on query intent
  6. Cross-source queries — JOIN across platforms for unified spend, ROAS, reach
  7. Anomaly detection — flags high frequency, low quality score, poor viewability
  8. Week-over-week / period comparison built-in
  9. Insight narrator — LLM writes plain-English analyst summary of every result
 10. Upload registry with row counts and source badges
 11. Login/register with SQLite auth
 12. Compatible with langchain==1.2.17, langchain-core==1.3.3,
     langchain-openai==1.1.10, langchain-community==0.4.1 on Python 3.11
"""

import streamlit as st
import os
import re
import hashlib
import sqlite3
import uuid
import json
import io
import base64
from datetime import datetime, timedelta
from warnings import filterwarnings

filterwarnings("ignore")

st.set_page_config(
    page_title="CampaignIQ",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────
# DESIGN SYSTEM — Dark editorial + sharp data aesthetic
# Fonts: DM Mono (headers) + IBM Plex Sans (body)
# Palette: Near-black bg, electric green accent, cool blue
# ─────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
    --bg-root:       #080C10;
    --bg-surface:    #0D1117;
    --bg-card:       #121920;
    --bg-elevated:   #182030;
    --bg-input:      #0F1824;
    --accent:        #00E5A0;
    --accent-dim:    rgba(0,229,160,0.08);
    --accent-border: rgba(0,229,160,0.22);
    --blue:          #4A9EFF;
    --blue-dim:      rgba(74,158,255,0.08);
    --blue-border:   rgba(74,158,255,0.20);
    --amber:         #F5A623;
    --amber-dim:     rgba(245,166,35,0.08);
    --red:           #FF5C6A;
    --red-dim:       rgba(255,92,106,0.08);
    --purple:        #A78BFA;
    --purple-dim:    rgba(167,139,250,0.08);
    --text-100:      #EEF2F7;
    --text-200:      #B8C4D0;
    --text-300:      #7A8A9A;
    --text-400:      #455060;
    --border:        rgba(255,255,255,0.055);
    --border-focus:  rgba(0,229,160,0.40);
    --radius-xs:     4px;
    --radius-sm:     6px;
    --radius-md:     10px;
    --radius-lg:     14px;
    --radius-xl:     20px;
}

html, body, .stApp {
    background: var(--bg-root) !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    color: var(--text-100) !important;
}
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--bg-elevated); border-radius: 3px; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: var(--bg-surface) !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown span,
section[data-testid="stSidebar"] .stMarkdown li {
    color: var(--text-200) !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.82rem !important;
}

/* ── Brand header in sidebar ── */
.brand-box {
    padding: 1.4rem 1rem 1.1rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 0.9rem;
}
.brand-name {
    font-family: 'DM Mono', monospace;
    font-size: 1.05rem;
    font-weight: 500;
    color: var(--text-100);
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.brand-name .dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 6px var(--accent);
    flex-shrink: 0;
}
.brand-sub {
    font-size: 0.60rem;
    color: var(--text-400);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-top: 3px;
    padding-left: 18px;
}

/* ── User pill ── */
.user-pill {
    display: flex; align-items: center; gap: 0.55rem;
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 0.5rem 0.65rem;
    margin: 0.5rem 0;
}
.user-pill .av {
    width: 28px; height: 28px; border-radius: 50%;
    background: var(--accent-dim); border: 1px solid var(--accent-border);
    display: flex; align-items: center; justify-content: center;
    font-family: 'DM Mono', monospace; font-weight: 500;
    font-size: 0.72rem; color: var(--accent); flex-shrink: 0;
}
.user-pill .nm { font-weight: 500; font-size: 0.80rem; color: var(--text-100); }
.user-pill .rl { font-size: 0.65rem; color: var(--text-400); }

/* ── Section divider ── */
.sd { border: none; border-top: 1px solid var(--border); margin: 0.85rem 0; }

/* ── Source badge chips ── */
.source-badge {
    display: inline-flex; align-items: center; gap: 0.3rem;
    border-radius: var(--radius-xs); padding: 0.18rem 0.55rem;
    font-size: 0.62rem; font-weight: 500;
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 0.04em; border: 1px solid;
}
.sb-sa360   { background: var(--blue-dim);   color: var(--blue);   border-color: var(--blue-border); }
.sb-gads    { background: var(--accent-dim); color: var(--accent); border-color: var(--accent-border); }
.sb-meta    { background: var(--purple-dim); color: var(--purple); border-color: rgba(167,139,250,0.20); }
.sb-dv360   { background: var(--amber-dim);  color: var(--amber);  border-color: rgba(245,166,35,0.20); }
.sb-ga4     { background: var(--red-dim);    color: var(--red);    border-color: rgba(255,92,106,0.20); }
.sb-custom  { background: rgba(255,255,255,0.04); color: var(--text-300); border-color: var(--border); }

/* ── Upload registry item ── */
.upload-item {
    display: flex; align-items: center; justify-content: space-between;
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 0.45rem 0.65rem;
    margin: 0.25rem 0;
}
.upload-item .ui-name { font-size: 0.75rem; color: var(--text-200); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 140px; }
.upload-item .ui-rows { font-family: 'IBM Plex Mono', monospace; font-size: 0.62rem; color: var(--text-400); }

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    padding: 0.85rem 1rem !important;
    margin-bottom: 0.55rem !important;
    color: var(--text-100) !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: var(--blue-dim) !important;
    border-color: var(--blue-border) !important;
}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] td,
[data-testid="stChatMessage"] span {
    color: var(--text-100) !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}
[data-testid="stChatMessage"] h1,
[data-testid="stChatMessage"] h2,
[data-testid="stChatMessage"] h3 {
    color: var(--accent) !important;
    font-family: 'DM Mono', monospace !important;
    font-weight: 500 !important;
}
[data-testid="stChatMessage"] code {
    background: rgba(0,229,160,0.06) !important;
    color: var(--accent) !important;
    font-family: 'IBM Plex Mono', monospace !important;
    padding: 0.12em 0.4em !important;
    border-radius: 3px !important;
    border: 1px solid var(--accent-border) !important;
}
[data-testid="stChatMessage"] pre {
    background: var(--bg-root) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
}
[data-testid="stChatMessage"] table th {
    background: var(--bg-elevated) !important;
    color: var(--accent) !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.78rem !important;
    border-bottom: 1px solid var(--accent-border) !important;
}
[data-testid="stChatMessage"] table td {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.80rem !important;
    border-bottom: 1px solid var(--border) !important;
}
[data-testid="stChatMessage"] blockquote {
    border-left: 3px solid var(--accent) !important;
    background: var(--accent-dim) !important;
    padding: 0.4em 0.9em !important;
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0 !important;
}

/* ── Tool badge ── */
.tool-badge {
    display: inline-flex; align-items: center; gap: 0.3rem;
    background: var(--bg-elevated); border: 1px solid var(--border);
    border-radius: var(--radius-xs); padding: 0.2rem 0.55rem;
    font-size: 0.65rem; color: var(--text-400);
    font-family: 'IBM Plex Mono', monospace;
    margin-right: 0.3rem; margin-top: 0.4rem;
}
.tool-badge .tb-dot {
    width: 5px; height: 5px; border-radius: 50%;
    background: var(--accent); flex-shrink: 0;
}

/* ── Insight card ── */
.insight-card {
    background: var(--accent-dim);
    border: 1px solid var(--accent-border);
    border-radius: var(--radius-md);
    padding: 0.85rem 1rem;
    margin: 0.6rem 0;
}
.insight-card .ic-label {
    font-size: 0.62rem; font-weight: 500;
    letter-spacing: 0.14em; text-transform: uppercase;
    color: var(--accent); font-family: 'DM Mono', monospace;
    margin-bottom: 0.4rem;
}
.insight-card .ic-text {
    font-size: 0.85rem; color: var(--text-200); line-height: 1.55;
}

/* ── Anomaly banner ── */
.anomaly-banner {
    background: var(--red-dim); border: 1px solid rgba(255,92,106,0.25);
    border-radius: var(--radius-sm); padding: 0.5rem 0.85rem;
    font-size: 0.80rem; color: var(--red); margin: 0.4rem 0;
}

/* ── Welcome area ── */
.welcome-area {
    text-align: center; padding: 9vh 2rem 3rem;
}
.welcome-area .w-logo {
    font-family: 'DM Mono', monospace;
    font-size: 2.4rem; font-weight: 300;
    color: var(--text-100); margin-bottom: 0.6rem;
    letter-spacing: -0.02em;
}
.welcome-area .w-logo span { color: var(--accent); }
.welcome-area .w-sub {
    font-size: 0.88rem; color: var(--text-400);
    max-width: 520px; margin: 0 auto 1.8rem; line-height: 1.65;
}
.prompt-grid {
    display: grid; grid-template-columns: repeat(2, 1fr);
    gap: 0.7rem; max-width: 680px; margin: 0 auto;
}
.prompt-chip {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 0.65rem 0.85rem;
    font-size: 0.78rem; color: var(--text-300);
    text-align: left; line-height: 1.45; cursor: pointer;
    transition: border-color 0.15s, color 0.15s;
}
.prompt-chip:hover { border-color: var(--accent-border); color: var(--text-100); }
.prompt-chip .pc-src {
    font-size: 0.62rem; color: var(--text-400);
    font-family: 'IBM Plex Mono', monospace;
    display: block; margin-bottom: 0.2rem;
}

/* ── Login ── */
.login-wrap { max-width: 420px; margin: 0 auto; padding: 8vh 1rem 3rem; }
.login-logo {
    font-family: 'DM Mono', monospace;
    font-size: 1.8rem; font-weight: 300;
    color: var(--text-100); text-align: center;
    margin-bottom: 0.3rem; letter-spacing: -0.02em;
}
.login-logo span { color: var(--accent); }
.login-tag {
    text-align: center; font-size: 0.68rem;
    color: var(--text-400); letter-spacing: 0.18em;
    text-transform: uppercase; margin-bottom: 2rem;
}
.login-feats {
    display: flex; flex-wrap: wrap; justify-content: center;
    gap: 0.5rem; margin-bottom: 1.8rem;
}
.lf-pill {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 20px; padding: 0.22rem 0.75rem;
    font-size: 0.68rem; color: var(--text-300);
    display: flex; align-items: center; gap: 0.3rem;
}
.lf-pill::before {
    content: ''; display: inline-block;
    width: 5px; height: 5px; border-radius: 50%;
    background: var(--accent); flex-shrink: 0;
}

/* ── Form inputs ── */
.stTextInput > div > div > input {
    background: var(--bg-input) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-100) !important;
    border-radius: var(--radius-sm) !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.85rem !important;
}
.stTextInput > div > div > input:focus {
    border-color: var(--border-focus) !important;
    box-shadow: 0 0 0 3px rgba(0,229,160,0.08) !important;
}
.stTextInput > div > div > input::placeholder { color: var(--text-400) !important; }

/* ── Buttons ── */
.stButton > button {
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-weight: 500 !important;
    border-radius: var(--radius-sm) !important;
    font-size: 0.83rem !important;
    transition: all 0.18s !important;
}
form .stButton > button {
    background: var(--accent) !important;
    color: #080C10 !important;
    border: none !important;
    font-weight: 600 !important;
}
form .stButton > button:hover { opacity: 0.88 !important; }
section[data-testid="stSidebar"] .stButton > button {
    background: var(--bg-card) !important;
    color: var(--text-200) !important;
    border: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--bg-elevated) !important;
    border-color: var(--accent-border) !important;
    color: var(--text-100) !important;
}

/* ── File uploader ── */
.stFileUploader > div {
    background: var(--bg-card) !important;
    border: 1px dashed rgba(0,229,160,0.15) !important;
    border-radius: var(--radius-sm) !important;
}

/* ── Chat input ── */
.stChatInput > div {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
}
.stChatInput textarea {
    color: var(--text-100) !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}

/* ── Spinner ── */
.stSpinner > div > div { border-top-color: var(--accent) !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0; border-bottom: 1px solid var(--border);
    background: transparent !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-300) !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    padding: 0.55rem 1.1rem !important;
    border-bottom: 2px solid transparent !important;
}
.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom-color: var(--accent) !important;
}

/* ── Alerts ── */
.stAlert { border-radius: var(--radius-sm) !important; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# DATABASE — Auth + upload registry + conversations
# ═══════════════════════════════════════════════════════

DB_PATH = "campaigniq.db"

# Column signatures to auto-detect source type
SOURCE_SIGNATURES = {
    "sa360": {
        "required": {"campaign", "impressions", "clicks", "cost"},
        "hints":    {"bid_strategy", "conversion_rate", "search_impr_share",
                     "engine", "search_engine", "device_type"}
    },
    "gads": {
        "required": {"campaign", "impressions", "clicks", "cost"},
        "hints":    {"quality_score", "ad_group", "keyword", "match_type",
                     "cpc", "roas", "avg_cpc"}
    },
    "meta": {
        "required": {"campaign_name", "reach", "impressions"},
        "hints":    {"frequency", "cpm", "objective", "ad_set",
                     "result_rate", "link_clicks"}
    },
    "dv360": {
        "required": {"impressions", "clicks"},
        "hints":    {"viewability_rate", "vtr", "line_item", "placement",
                     "active_view", "trueview", "io_name"}
    },
    "ga4": {
        "required": {"sessions"},
        "hints":    {"bounce_rate", "avg_session_duration", "pageviews",
                     "new_users", "source_medium", "conversion_rate",
                     "goal_completions"}
    },
}


def init_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Auth tables
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id      TEXT PRIMARY KEY,
        username     TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        display_name TEXT,
        role         TEXT DEFAULT 'analyst',
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # Conversation tables
    c.execute("""CREATE TABLE IF NOT EXISTS conversations (
        conversation_id TEXT PRIMARY KEY,
        user_id         TEXT NOT NULL,
        title           TEXT DEFAULT 'New session',
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        message_id      TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        role            TEXT NOT NULL,
        content         TEXT NOT NULL,
        tool_used       TEXT,
        sources_used    TEXT,
        timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # Upload registry
    c.execute("""CREATE TABLE IF NOT EXISTS uploads_registry (
        upload_id    TEXT PRIMARY KEY,
        user_id      TEXT NOT NULL,
        filename     TEXT NOT NULL,
        source_type  TEXT NOT NULL,
        table_name   TEXT NOT NULL,
        row_count    INT  DEFAULT 0,
        columns_json TEXT,
        uploaded_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # ── Campaign data tables (created once, rows appended per upload) ──
    c.execute("""CREATE TABLE IF NOT EXISTS sa360_campaigns (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        upload_id       TEXT,
        date            TEXT,
        campaign        TEXT,
        impressions     REAL,
        clicks          REAL,
        cost            REAL,
        conversions     REAL,
        ctr             REAL,
        cpc             REAL,
        conversion_rate REAL,
        bid_strategy    TEXT,
        device_type     TEXT,
        engine          TEXT,
        search_impr_share REAL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS gads_performance (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        upload_id       TEXT,
        date            TEXT,
        campaign        TEXT,
        ad_group        TEXT,
        keyword         TEXT,
        match_type      TEXT,
        impressions     REAL,
        clicks          REAL,
        cost            REAL,
        cpc             REAL,
        roas            REAL,
        conversions     REAL,
        ctr             REAL,
        quality_score   REAL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS meta_ads (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        upload_id       TEXT,
        date            TEXT,
        campaign_name   TEXT,
        ad_set          TEXT,
        objective       TEXT,
        reach           REAL,
        impressions     REAL,
        frequency       REAL,
        clicks          REAL,
        ctr             REAL,
        cpm             REAL,
        spend           REAL,
        result_rate     REAL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS dv360_display (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        upload_id       TEXT,
        date            TEXT,
        line_item       TEXT,
        placement       TEXT,
        impressions     REAL,
        clicks          REAL,
        viewability_rate REAL,
        vtr             REAL,
        cpm             REAL,
        cost            REAL,
        active_view_rate REAL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS ga4_analytics (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        upload_id            TEXT,
        date                 TEXT,
        source_medium        TEXT,
        sessions             REAL,
        new_users            REAL,
        pageviews            REAL,
        bounce_rate          REAL,
        avg_session_duration REAL,
        conversions          REAL,
        conversion_rate      REAL,
        goal_completions     REAL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS custom_uploads (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        upload_id  TEXT,
        data_json  TEXT
    )""")

    conn.commit()
    conn.close()


def _hash(pw):
    return hashlib.sha256(f"campaigniq_salt_2025_{pw}".encode()).hexdigest()


def register_user(username, password):
    uid = str(uuid.uuid4())
    display = username.strip().title()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO users VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)",
            (uid, username.lower().strip(), _hash(password), display, "analyst")
        )
        conn.commit()
        conn.close()
        return {"user_id": uid, "username": username.lower().strip(),
                "display_name": display, "role": "analyst"}
    except sqlite3.IntegrityError:
        conn.close()
        return None


def authenticate(username, password):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT user_id,username,display_name,role FROM users "
        "WHERE username=? AND password_hash=?",
        (username.lower().strip(), _hash(password))
    ).fetchone()
    conn.close()
    if row:
        return {"user_id": row[0], "username": row[1],
                "display_name": row[2], "role": row[3]}
    return None


def seed_defaults():
    conn = sqlite3.connect(DB_PATH)
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        conn.execute(
            "INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)",
            (str(uuid.uuid4()), "admin", _hash("admin123"), "Admin", "admin")
        )
        conn.commit()
    conn.close()


def create_conversation(uid, title="New session"):
    cid = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO conversations VALUES (?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)",
        (cid, uid, title)
    )
    conn.commit()
    conn.close()
    return cid


def get_conversations(uid):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT conversation_id,title,updated_at FROM conversations "
        "WHERE user_id=? ORDER BY updated_at DESC",
        (uid,)
    ).fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "updated_at": r[2]} for r in rows]


def delete_conversation(cid):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM messages WHERE conversation_id=?", (cid,))
    conn.execute("DELETE FROM conversations WHERE conversation_id=?", (cid,))
    conn.commit()
    conn.close()


def save_message(cid, role, content, tool_used=None, sources_used=None):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO messages VALUES (?,?,?,?,?,?,CURRENT_TIMESTAMP)",
        (str(uuid.uuid4()), cid, role, content, tool_used,
         json.dumps(sources_used) if sources_used else None)
    )
    conn.execute(
        "UPDATE conversations SET updated_at=CURRENT_TIMESTAMP "
        "WHERE conversation_id=?", (cid,)
    )
    conn.commit()
    conn.close()


def get_messages(cid):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT role,content,tool_used,sources_used,timestamp "
        "FROM messages WHERE conversation_id=? ORDER BY timestamp ASC",
        (cid,)
    ).fetchall()
    conn.close()
    out = []
    for r in rows:
        s = None
        if r[3]:
            try:
                s = json.loads(r[3])
            except Exception:
                pass
        out.append({"role": r[0], "content": r[1],
                    "tool_used": r[2], "sources": s, "timestamp": r[4]})
    return out


def get_uploads(uid):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT upload_id,filename,source_type,table_name,row_count,uploaded_at "
        "FROM uploads_registry WHERE user_id=? ORDER BY uploaded_at DESC",
        (uid,)
    ).fetchall()
    conn.close()
    return [{"id": r[0], "filename": r[1], "source_type": r[2],
             "table_name": r[3], "row_count": r[4], "uploaded_at": r[5]}
            for r in rows]


def delete_upload(upload_id, table_name, uid):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(f"DELETE FROM {table_name} WHERE upload_id=?", (upload_id,))
    conn.execute(
        "DELETE FROM uploads_registry WHERE upload_id=? AND user_id=?",
        (upload_id, uid)
    )
    conn.commit()
    conn.close()


def generate_title(prompt):
    words = prompt.strip().split()
    return " ".join(words[:6]) + ("…" if len(words) > 6 else "")


# ═══════════════════════════════════════════════════════
# SOURCE DETECTION & INGESTION
# ═══════════════════════════════════════════════════════

def normalise_col(col: str) -> str:
    return col.strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_")


def detect_source(df_cols: list) -> str:
    """
    Identify the platform by column overlap scoring.
    Returns one of: sa360 | gads | meta | dv360 | ga4 | custom
    """
    import pandas as pd
    norm = {normalise_col(c) for c in df_cols}

    scores = {}
    for src, sig in SOURCE_SIGNATURES.items():
        required_hit = len(sig["required"] & norm)
        hint_hit     = len(sig["hints"]    & norm)
        # required columns are worth 3 points each, hints 1 point
        scores[src] = required_hit * 3 + hint_hit

    best = max(scores, key=scores.get)
    if scores[best] >= 6:      # minimum threshold
        return best
    return "custom"


def ingest_csv(file_obj, uid: str):
    """
    Read CSV/Excel, detect source, write rows to the right table.
    Returns (source_type, table_name, row_count, upload_id, columns)
    """
    import pandas as pd

    fname = file_obj.name.lower()
    if fname.endswith((".xlsx", ".xls")):
        df = pd.read_excel(file_obj)
    else:
        file_obj.seek(0)
        df = pd.read_csv(file_obj)

    # Normalise column names
    df.columns = [normalise_col(c) for c in df.columns]
    df = df.dropna(how="all")

    source_type = detect_source(df.columns.tolist())
    upload_id   = str(uuid.uuid4())
    row_count   = len(df)
    columns     = df.columns.tolist()

    table_map = {
        "sa360":  ("sa360_campaigns",  _insert_sa360),
        "gads":   ("gads_performance", _insert_gads),
        "meta":   ("meta_ads",         _insert_meta),
        "dv360":  ("dv360_display",    _insert_dv360),
        "ga4":    ("ga4_analytics",    _insert_ga4),
        "custom": ("custom_uploads",   _insert_custom),
    }

    table_name, insert_fn = table_map[source_type]
    insert_fn(df, upload_id)

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO uploads_registry VALUES (?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
        (upload_id, uid, file_obj.name, source_type,
         table_name, row_count, json.dumps(columns))
    )
    conn.commit()
    conn.close()

    return source_type, table_name, row_count, upload_id, columns


def _g(df, col, default=None):
    """Safe column getter — returns series or default."""
    import pandas as pd
    for c in df.columns:
        if c == col:
            return df[col]
    # Try partial match
    for c in df.columns:
        if col in c:
            return df[c]
    return pd.Series([default] * len(df))


def _insert_sa360(df, uid):
    import pandas as pd
    conn = sqlite3.connect(DB_PATH)
    for _, row in df.iterrows():
        conn.execute("""
            INSERT INTO sa360_campaigns
            (upload_id,date,campaign,impressions,clicks,cost,conversions,
             ctr,cpc,conversion_rate,bid_strategy,device_type,engine,search_impr_share)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            uid,
            str(row.get("date", "")),
            str(row.get("campaign", row.get("campaign_name", ""))),
            _safe_float(row, "impressions"),
            _safe_float(row, "clicks"),
            _safe_float(row, "cost"),
            _safe_float(row, "conversions"),
            _safe_float(row, "ctr"),
            _safe_float(row, "cpc"),
            _safe_float(row, "conversion_rate"),
            str(row.get("bid_strategy", "")),
            str(row.get("device_type", "")),
            str(row.get("engine", row.get("search_engine", ""))),
            _safe_float(row, "search_impr_share"),
        ))
    conn.commit()
    conn.close()


def _insert_gads(df, uid):
    conn = sqlite3.connect(DB_PATH)
    for _, row in df.iterrows():
        conn.execute("""
            INSERT INTO gads_performance
            (upload_id,date,campaign,ad_group,keyword,match_type,
             impressions,clicks,cost,cpc,roas,conversions,ctr,quality_score)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            uid,
            str(row.get("date", "")),
            str(row.get("campaign", row.get("campaign_name", ""))),
            str(row.get("ad_group", "")),
            str(row.get("keyword", "")),
            str(row.get("match_type", "")),
            _safe_float(row, "impressions"),
            _safe_float(row, "clicks"),
            _safe_float(row, "cost"),
            _safe_float(row, "cpc"),
            _safe_float(row, "roas"),
            _safe_float(row, "conversions"),
            _safe_float(row, "ctr"),
            _safe_float(row, "quality_score"),
        ))
    conn.commit()
    conn.close()


def _insert_meta(df, uid):
    conn = sqlite3.connect(DB_PATH)
    for _, row in df.iterrows():
        conn.execute("""
            INSERT INTO meta_ads
            (upload_id,date,campaign_name,ad_set,objective,reach,impressions,
             frequency,clicks,ctr,cpm,spend,result_rate)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            uid,
            str(row.get("date", "")),
            str(row.get("campaign_name", row.get("campaign", ""))),
            str(row.get("ad_set", row.get("adset_name", ""))),
            str(row.get("objective", "")),
            _safe_float(row, "reach"),
            _safe_float(row, "impressions"),
            _safe_float(row, "frequency"),
            _safe_float(row, "clicks", row.get("link_clicks")),
            _safe_float(row, "ctr"),
            _safe_float(row, "cpm"),
            _safe_float(row, "spend", row.get("amount_spent")),
            _safe_float(row, "result_rate"),
        ))
    conn.commit()
    conn.close()


def _insert_dv360(df, uid):
    conn = sqlite3.connect(DB_PATH)
    for _, row in df.iterrows():
        conn.execute("""
            INSERT INTO dv360_display
            (upload_id,date,line_item,placement,impressions,clicks,
             viewability_rate,vtr,cpm,cost,active_view_rate)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            uid,
            str(row.get("date", "")),
            str(row.get("line_item", row.get("line_item_name", ""))),
            str(row.get("placement", row.get("site", ""))),
            _safe_float(row, "impressions"),
            _safe_float(row, "clicks"),
            _safe_float(row, "viewability_rate", row.get("active_view_viewability")),
            _safe_float(row, "vtr"),
            _safe_float(row, "cpm"),
            _safe_float(row, "cost", row.get("revenue_usd")),
            _safe_float(row, "active_view_rate"),
        ))
    conn.commit()
    conn.close()


def _insert_ga4(df, uid):
    conn = sqlite3.connect(DB_PATH)
    for _, row in df.iterrows():
        conn.execute("""
            INSERT INTO ga4_analytics
            (upload_id,date,source_medium,sessions,new_users,pageviews,
             bounce_rate,avg_session_duration,conversions,conversion_rate,goal_completions)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            uid,
            str(row.get("date", "")),
            str(row.get("source_medium", row.get("source___medium", ""))),
            _safe_float(row, "sessions"),
            _safe_float(row, "new_users"),
            _safe_float(row, "pageviews"),
            _safe_float(row, "bounce_rate"),
            _safe_float(row, "avg_session_duration"),
            _safe_float(row, "conversions", row.get("goal_completions")),
            _safe_float(row, "conversion_rate"),
            _safe_float(row, "goal_completions"),
        ))
    conn.commit()
    conn.close()


def _insert_custom(df, uid):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO custom_uploads (upload_id, data_json) VALUES (?,?)",
        (uid, df.to_json(orient="records"))
    )
    conn.commit()
    conn.close()


def _safe_float(row, *keys):
    for k in keys:
        if k and k in row:
            try:
                v = row[k]
                if v is None or (isinstance(v, float) and __import__("math").isnan(v)):
                    continue
                return float(str(v).replace(",", "").replace("%", "").strip())
            except Exception:
                continue
    return None


# ═══════════════════════════════════════════════════════
# LLM HELPER
# ═══════════════════════════════════════════════════════

def get_llm(max_tokens=2000):
    from langchain_openai import AzureChatOpenAI
    return AzureChatOpenAI(
        azure_deployment="gpt-4o",
        api_version="2024-12-01-preview",
        azure_endpoint=st.session_state.get("azure_endpoint", ""),
        api_key=st.session_state.get("azure_api_key", ""),
        temperature=0,
        max_tokens=max_tokens,
    )


# ═══════════════════════════════════════════════════════
# CHART ROUTER — auto-picks the best chart type
# ═══════════════════════════════════════════════════════

def pick_chart_type(query: str, df) -> str:
    q = query.lower()
    if any(w in q for w in ["trend", "over time", "week", "month", "daily", "wow",
                              "timeline", "history", "evolution"]):
        return "line"
    if any(w in q for w in ["share", "breakdown", "split", "proportion",
                              "percentage of", "% of", "portion"]):
        return "pie"
    if any(w in q for w in ["scatter", "correlation", "relationship between",
                              "vs ", "versus", "plotted"]):
        return "scatter"
    if any(w in q for w in ["distribution", "histogram", "frequency"]):
        return "hist"
    return "bar"


def render_chart(df, chart_type: str, title: str, x_col: str, y_col: str):
    """
    Generate a styled matplotlib figure.
    Returns the figure object.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    COLORS = ["#00E5A0", "#4A9EFF", "#F5A623", "#A78BFA",
              "#FF5C6A", "#00C4B3", "#FFB347", "#6B8AFF"]
    BG     = "#0D1117"
    GRID   = "#182030"
    TEXT   = "#B8C4D0"
    TITLE  = "#EEF2F7"

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    try:
        if chart_type == "line":
            for i, col in enumerate(df.select_dtypes("number").columns[:5]):
                ax.plot(df[x_col] if x_col in df.columns else df.index,
                        df[col], color=COLORS[i % len(COLORS)],
                        linewidth=2, marker="o", markersize=4, label=col)
            ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=TEXT, fontsize=9)

        elif chart_type == "pie":
            vals = df[y_col].values
            labs = df[x_col].values if x_col in df.columns else df.index
            wedges, texts, autotexts = ax.pie(
                vals, labels=labs,
                colors=COLORS[:len(vals)],
                autopct="%1.1f%%",
                textprops={"color": TEXT, "fontsize": 9},
                startangle=90, pctdistance=0.80
            )
            for at in autotexts:
                at.set_color(BG)
                at.set_fontsize(8)

        elif chart_type == "scatter":
            num_cols = df.select_dtypes("number").columns.tolist()
            if len(num_cols) >= 2:
                ax.scatter(df[num_cols[0]], df[num_cols[1]],
                           color=COLORS[0], alpha=0.7, edgecolors="none", s=50)
                ax.set_xlabel(num_cols[0], color=TEXT, fontsize=9)
                ax.set_ylabel(num_cols[1], color=TEXT, fontsize=9)

        elif chart_type == "hist":
            num_cols = df.select_dtypes("number").columns.tolist()
            if num_cols:
                ax.hist(df[num_cols[0]].dropna(), bins=20,
                        color=COLORS[0], edgecolor=BG, alpha=0.9)
                ax.set_xlabel(num_cols[0], color=TEXT, fontsize=9)

        else:  # bar
            x_vals = df[x_col].astype(str) if x_col in df.columns else df.index.astype(str)
            y_vals = df[y_col] if y_col in df.columns else df.iloc[:, -1]
            bars = ax.bar(range(len(x_vals)), y_vals,
                          color=COLORS[0], edgecolor=BG, linewidth=0.5)
            # Gradient effect — colour bars by value intensity
            if len(y_vals) > 1:
                mn, mx = y_vals.min(), y_vals.max()
                for bar, val in zip(bars, y_vals):
                    if mx > mn:
                        t = (val - mn) / (mx - mn)
                        r1, g1, b1 = 0x4A/255, 0x9E/255, 0xFF/255
                        r2, g2, b2 = 0x00/255, 0xE5/255, 0xA0/255
                        bar.set_facecolor((r1*(1-t)+r2*t, g1*(1-t)+g2*t, b1*(1-t)+b2*t))
            ax.set_xticks(range(len(x_vals)))
            ax.set_xticklabels(x_vals, rotation=35, ha="right",
                               fontsize=8, color=TEXT)

        ax.set_title(title, color=TITLE, fontsize=11, fontweight="bold", pad=12)
        ax.tick_params(colors=TEXT, labelsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(GRID)
        ax.spines["bottom"].set_color(GRID)
        ax.yaxis.grid(True, color=GRID, linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True)
        plt.tight_layout()
    except Exception as e:
        ax.text(0.5, 0.5, f"Chart error: {e}", transform=ax.transAxes,
                color=TEXT, ha="center", va="center")

    return fig


# ═══════════════════════════════════════════════════════
# QUERY ENGINE — NL → SQL → results → insight
# ═══════════════════════════════════════════════════════

# Full schema description passed to the LLM so it can write accurate SQL
SCHEMA_PROMPT = """
You have access to a SQLite database with these tables:

sa360_campaigns(id, upload_id, date, campaign, impressions, clicks, cost, conversions,
  ctr, cpc, conversion_rate, bid_strategy, device_type, engine, search_impr_share)

gads_performance(id, upload_id, date, campaign, ad_group, keyword, match_type,
  impressions, clicks, cost, cpc, roas, conversions, ctr, quality_score)

meta_ads(id, upload_id, date, campaign_name, ad_set, objective, reach, impressions,
  frequency, clicks, ctr, cpm, spend, result_rate)

dv360_display(id, upload_id, date, line_item, placement, impressions, clicks,
  viewability_rate, vtr, cpm, cost, active_view_rate)

ga4_analytics(id, upload_id, date, source_medium, sessions, new_users, pageviews,
  bounce_rate, avg_session_duration, conversions, conversion_rate, goal_completions)

custom_uploads(id, upload_id, data_json)

uploads_registry(upload_id, user_id, filename, source_type, table_name, row_count,
  columns_json, uploaded_at)

IMPORTANT RULES:
- Always use ROUND(value, 2) for floats in SELECT
- For CTR / rates stored as decimals (0.05), multiply by 100 in display: ROUND(ctr*100,2)||'%'
- For cost / spend, prefix with '$': '$'||ROUND(cost,2)
- NULL values are common — use COALESCE(col, 0) for aggregations
- Dates are stored as TEXT 'YYYY-MM-DD'; use strftime for grouping
- Limit all results to 20 rows unless the user asks for more
- Only query tables that have data (check uploads_registry)
- When comparing across platforms, alias each source clearly
"""


def tables_with_data(uid: str) -> list:
    """Return list of table names that have data for this user."""
    uploads = get_uploads(uid)
    return list({u["table_name"] for u in uploads})


def run_insight_query(prompt: str, uid: str):
    """
    Main pipeline:
      1. Ask LLM to write SQL given the schema
      2. Execute SQL against SQLite
      3. Ask LLM to narrate the results
      4. Auto-render chart if query returns tabular data
    Returns (answer_text, fig_or_None, sql_used, tool_tag)
    """
    import pandas as pd
    from langchain_core.messages import SystemMessage, HumanMessage

    available = tables_with_data(uid)
    if not available:
        return (
            "No campaign data has been uploaded yet. "
            "Please upload a CSV from SA360, Google Ads, Meta, DV360, or GA4 "
            "using the sidebar uploader.",
            None, None, "No data"
        )

    llm = get_llm(max_tokens=600)

    # Step 1 — Generate SQL
    sql_system = (
        SCHEMA_PROMPT +
        f"\n\nTables that currently have data: {available}\n"
        "ONLY query these tables. "
        "Return ONLY the SQL query — no explanation, no markdown fences, no commentary."
    )
    sql_resp = llm.invoke([
        SystemMessage(content=sql_system),
        HumanMessage(content=f"Write a SQLite query to answer: {prompt}")
    ])
    raw_sql = sql_resp.content.strip()
    # Clean up any accidental fences
    for fence in ["```sql", "```sqlite", "```"]:
        raw_sql = raw_sql.replace(fence, "")
    sql = raw_sql.strip()

    # Step 2 — Execute
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(sql, conn)
        conn.close()
    except Exception as e:
        return (
            f"**SQL execution error:** `{e}`\n\n"
            f"Generated query:\n```sql\n{sql}\n```\n\n"
            "Try rephrasing your question or check that you have uploaded the relevant data source.",
            None, sql, "SQL Error"
        )

    if df.empty:
        return (
            "The query returned no rows. This may mean:\n"
            "- The relevant data source hasn't been uploaded yet\n"
            "- The filter criteria matched nothing (e.g. a date range with no data)\n\n"
            f"Query used:\n```sql\n{sql}\n```",
            None, sql, "Empty result"
        )

    # Step 3 — Narrate
    preview = df.head(15).to_markdown(index=False)
    narrate_system = (
        "You are a senior marketing analyst. "
        "Given query results, write a sharp 3-5 sentence insight. "
        "Highlight the most important number, trend, or anomaly. "
        "Use bold for key metrics. Be specific — cite actual values from the data. "
        "End with one actionable recommendation."
    )
    narrate_resp = llm.invoke([
        SystemMessage(content=narrate_system),
        HumanMessage(content=(
            f"Question: {prompt}\n\nQuery results:\n{preview}\n\n"
            "Write the insight:"
        ))
    ])
    narrative = narrate_resp.content.strip()

    full_answer = (
        f"{narrative}\n\n"
        f"---\n\n"
        f"{df.head(20).to_markdown(index=False)}\n\n"
        f"<details><summary>SQL used</summary>\n\n```sql\n{sql}\n```\n</details>"
    )

    # Step 4 — Chart
    fig = None
    wants_chart = any(kw in prompt.lower() for kw in [
        "chart", "plot", "graph", "visuali", "show", "bar", "pie", "line",
        "trend", "compare", "breakdown", "distribution"
    ])
    num_cols   = df.select_dtypes("number").columns.tolist()
    str_cols   = df.select_dtypes("object").columns.tolist()

    if wants_chart and len(num_cols) >= 1:
        chart_type = pick_chart_type(prompt, df)
        x_col = str_cols[0] if str_cols else (df.columns[0])
        y_col = num_cols[0]
        chart_df = df.head(20).copy()
        # For numeric x (like quality_score scatter), keep as-is
        fig = render_chart(chart_df, chart_type, prompt[:60], x_col, y_col)

    tool_tag = f"SQL · {' + '.join(available)}"
    return full_answer, fig, sql, tool_tag


# ═══════════════════════════════════════════════════════
# ANOMALY DETECTION — always-on passive checks
# ═══════════════════════════════════════════════════════

def run_anomaly_checks(uid: str) -> list:
    """
    Run lightweight passive anomaly checks across uploaded data.
    Returns list of warning strings.
    """
    available = tables_with_data(uid)
    warnings  = []
    conn      = sqlite3.connect(DB_PATH)

    try:
        if "meta_ads" in available:
            rows = conn.execute(
                "SELECT campaign_name, ROUND(AVG(frequency),2) as avg_freq "
                "FROM meta_ads GROUP BY campaign_name "
                "HAVING avg_freq > 3.5 ORDER BY avg_freq DESC LIMIT 3"
            ).fetchall()
            for r in rows:
                warnings.append(
                    f"⚠️ Meta: **{r[0]}** has avg frequency **{r[1]}** "
                    f"(>3.5 — ad fatigue risk)"
                )

        if "gads_performance" in available:
            rows = conn.execute(
                "SELECT keyword, ROUND(AVG(quality_score),1) as qs "
                "FROM gads_performance WHERE quality_score IS NOT NULL "
                "AND quality_score < 5 AND cost > 0 "
                "GROUP BY keyword ORDER BY qs ASC LIMIT 3"
            ).fetchall()
            for r in rows:
                warnings.append(
                    f"⚠️ Google Ads: keyword **\"{r[0]}\"** has quality score **{r[1]}/10** "
                    f"— check landing page & ad relevance"
                )

        if "dv360_display" in available:
            rows = conn.execute(
                "SELECT placement, ROUND(AVG(viewability_rate)*100,1) as vr "
                "FROM dv360_display WHERE viewability_rate IS NOT NULL "
                "GROUP BY placement HAVING vr < 50 ORDER BY vr ASC LIMIT 3"
            ).fetchall()
            for r in rows:
                warnings.append(
                    f"⚠️ DV360: placement **{r[0]}** has viewability **{r[1]}%** "
                    f"(industry benchmark: 70%+)"
                )

        if "sa360_campaigns" in available:
            rows = conn.execute(
                "SELECT campaign, ROUND(SUM(cost),2) as total_cost, "
                "ROUND(AVG(ctr)*100,2) as avg_ctr "
                "FROM sa360_campaigns GROUP BY campaign "
                "HAVING total_cost > 0 AND avg_ctr < 0.5 "
                "ORDER BY total_cost DESC LIMIT 3"
            ).fetchall()
            for r in rows:
                warnings.append(
                    f"⚠️ SA360: **{r[0]}** spent **${r[1]}** with only "
                    f"**{r[2]}% CTR** — review ad copy & targeting"
                )
    except Exception:
        pass
    finally:
        conn.close()

    return warnings


# ═══════════════════════════════════════════════════════
# RENDER — LOGIN
# ═══════════════════════════════════════════════════════

def render_login():
    st.markdown(
        "<style>section[data-testid='stSidebar']{display:none;}</style>",
        unsafe_allow_html=True
    )
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown("""
        <div class="login-wrap">
            <div class="login-logo">Campaign<span>IQ</span></div>
            <div class="login-tag">Marketing Intelligence Platform</div>
            <div class="login-feats">
                <span class="lf-pill">SA360</span>
                <span class="lf-pill">Google Ads</span>
                <span class="lf-pill">Meta Ads</span>
                <span class="lf-pill">DV360</span>
                <span class="lf-pill">GA4</span>
                <span class="lf-pill">SQL Insights</span>
                <span class="lf-pill">Auto-charts</span>
                <span class="lf-pill">Anomaly alerts</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        t1, t2 = st.tabs(["Sign in", "Create account"])

        with t1:
            with st.form("login_form", clear_on_submit=False):
                u = st.text_input("Username", placeholder="your.username", key="l_u")
                p = st.text_input("Password", type="password", placeholder="••••••••", key="l_p")
                if st.form_submit_button("Sign in →", use_container_width=True):
                    if u and p:
                        user = authenticate(u, p)
                        if user:
                            st.session_state.update(
                                authenticated=True, user=user,
                                current_conv=None, messages=[]
                            )
                            st.rerun()
                        else:
                            st.error("Invalid credentials.")
                    else:
                        st.warning("Fill in both fields.")

        with t2:
            with st.form("signup_form", clear_on_submit=True):
                nu = st.text_input("Username", placeholder="e.g. alice.wong", key="s_u")
                p1 = st.text_input("Password", type="password",
                                   placeholder="Min 4 chars", key="s_p1")
                p2 = st.text_input("Confirm", type="password", key="s_p2")
                if st.form_submit_button("Create account →", use_container_width=True):
                    nc = (nu or "").strip()
                    if not nc or not p1:
                        st.warning("All fields required.")
                    elif len(nc) < 3:
                        st.warning("Username must be 3+ chars.")
                    elif len(p1) < 4:
                        st.warning("Password must be 4+ chars.")
                    elif p1 != p2:
                        st.error("Passwords don't match.")
                    else:
                        r = register_user(nc, p1)
                        if r:
                            st.success(f"Account created — sign in as **{nc}**")
                        else:
                            st.error("Username already taken.")

        st.markdown(
            "<p style='text-align:center;color:var(--text-400);"
            "font-size:0.65rem;margin-top:1.2rem;'>"
            "CampaignIQ v1.0 · Secure & Confidential</p>",
            unsafe_allow_html=True
        )


# ═══════════════════════════════════════════════════════
# RENDER — SIDEBAR
# ═══════════════════════════════════════════════════════

SOURCE_CLASS = {
    "sa360":  "sb-sa360",
    "gads":   "sb-gads",
    "meta":   "sb-meta",
    "dv360":  "sb-dv360",
    "ga4":    "sb-ga4",
    "custom": "sb-custom",
}
SOURCE_LABEL = {
    "sa360":  "SA360",
    "gads":   "Google Ads",
    "meta":   "Meta",
    "dv360":  "DV360",
    "ga4":    "GA4",
    "custom": "Custom",
}


def render_sidebar():
    user = st.session_state["user"]
    with st.sidebar:
        # Brand
        st.markdown(
            '<div class="brand-box">'
            '<div class="brand-name"><span class="dot"></span>CampaignIQ</div>'
            '<div class="brand-sub">Marketing Intelligence</div>'
            '</div>',
            unsafe_allow_html=True
        )

        # User pill
        ini = user["display_name"][0].upper()
        st.markdown(
            f'<div class="user-pill">'
            f'<div class="av">{ini}</div>'
            f'<div><div class="nm">{user["display_name"]}</div>'
            f'<div class="rl">{user["role"].title()}</div></div>'
            f'</div>',
            unsafe_allow_html=True
        )

        st.markdown('<hr class="sd">', unsafe_allow_html=True)

        # API config
        with st.expander("🔑 API Configuration",
                         expanded=not st.session_state.get("azure_endpoint")):
            ep_val = st.text_input(
                "Azure OpenAI Endpoint",
                value=st.session_state.get("azure_endpoint", ""),
                placeholder="https://your-resource.openai.azure.com/",
                key="cfg_ep"
            )
            ak_val = st.text_input(
                "API Key",
                value=st.session_state.get("azure_api_key", ""),
                placeholder="Enter your key",
                key="cfg_key",
                type="password"
            )
            if st.button("Save credentials", use_container_width=True, key="save_cfg"):
                if ep_val.strip() and ak_val.strip():
                    st.session_state["azure_endpoint"] = ep_val.strip()
                    st.session_state["azure_api_key"]  = ak_val.strip()
                    st.success("Saved!")
                    st.rerun()
                else:
                    st.warning("Both fields required.")

        # New conversation
        if st.button("＋  New session", use_container_width=True, key="new_chat"):
            st.session_state["current_conv"] = None
            st.session_state["messages"] = []
            st.rerun()

        st.markdown('<hr class="sd">', unsafe_allow_html=True)

        # Upload section
        st.markdown(
            "<p style='font-size:0.70rem;font-weight:600;"
            "color:var(--text-400);letter-spacing:0.12em;"
            "text-transform:uppercase;'>Upload data</p>",
            unsafe_allow_html=True
        )
        st.caption(
            "Supports SA360, Google Ads, Meta Ads, DV360, GA4 exports "
            "and any custom CSV/XLSX. Source is auto-detected."
        )

        uploaded = st.file_uploader(
            "Drop CSV / Excel files",
            type=["csv", "xlsx", "xls"],
            accept_multiple_files=True,
            key="uploader"
        )

        if uploaded:
            for uf in uploaded:
                already = [
                    u["filename"] for u in get_uploads(user["user_id"])
                ]
                if uf.name not in already:
                    with st.spinner(f"Ingesting {uf.name}…"):
                        try:
                            src, tbl, rows, uid_up, cols = ingest_csv(
                                uf, user["user_id"]
                            )
                            sc = SOURCE_CLASS.get(src, "sb-custom")
                            sl = SOURCE_LABEL.get(src, src.upper())
                            st.success(
                                f"✓ {uf.name} → "
                                f"**{sl}** ({rows:,} rows)"
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"Ingest failed: {e}")

        st.markdown('<hr class="sd">', unsafe_allow_html=True)

        # Uploaded data registry
        uploads = get_uploads(user["user_id"])
        if uploads:
            st.markdown(
                "<p style='font-size:0.70rem;font-weight:600;"
                "color:var(--text-400);letter-spacing:0.12em;"
                "text-transform:uppercase;'>Loaded sources</p>",
                unsafe_allow_html=True
            )
            for u in uploads:
                sc = SOURCE_CLASS.get(u["source_type"], "sb-custom")
                sl = SOURCE_LABEL.get(u["source_type"], u["source_type"])
                col_a, col_b = st.columns([5, 1])
                with col_a:
                    st.markdown(
                        f'<div class="upload-item">'
                        f'<span class="ui-name" title="{u["filename"]}">'
                        f'{u["filename"]}</span>'
                        f'<span class="source-badge {sc}">{sl}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                    st.markdown(
                        f'<p style="font-size:0.62rem;color:var(--text-400);'
                        f'margin:-4px 0 4px 4px;">'
                        f'{u["row_count"]:,} rows</p>',
                        unsafe_allow_html=True
                    )
                with col_b:
                    if st.button("×", key=f"del_{u['id']}"):
                        delete_upload(u["id"], u["table_name"], user["user_id"])
                        st.rerun()
        else:
            st.caption("No data uploaded yet.")

        st.markdown('<hr class="sd">', unsafe_allow_html=True)

        # Conversation history
        st.markdown(
            "<p style='font-size:0.70rem;font-weight:600;"
            "color:var(--text-400);letter-spacing:0.12em;"
            "text-transform:uppercase;'>Sessions</p>",
            unsafe_allow_html=True
        )
        convs = get_conversations(user["user_id"])[:20]
        if convs:
            for c in convs:
                active = st.session_state.get("current_conv") == c["id"]
                c1, c2 = st.columns([6, 1])
                with c1:
                    label = ("▸ " if active else "") + c["title"][:32]
                    if st.button(label, key=f"cv_{c['id']}", use_container_width=True):
                        st.session_state["current_conv"] = c["id"]
                        st.session_state["messages"] = get_messages(c["id"])
                        st.rerun()
                with c2:
                    if st.button("×", key=f"dc_{c['id']}"):
                        delete_conversation(c["id"])
                        if st.session_state.get("current_conv") == c["id"]:
                            st.session_state["current_conv"] = None
                            st.session_state["messages"] = []
                        st.rerun()
        else:
            st.caption("No sessions yet.")

        st.markdown('<hr class="sd">', unsafe_allow_html=True)
        if st.button("Sign out", use_container_width=True, key="logout"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

        st.markdown(
            "<p style='color:var(--text-400);font-size:0.60rem;"
            "text-align:center;padding-top:0.6rem;'>"
            "CampaignIQ v1.0</p>",
            unsafe_allow_html=True
        )


# ═══════════════════════════════════════════════════════
# RENDER — CHAT
# ═══════════════════════════════════════════════════════

EXAMPLE_PROMPTS = [
    ("SA360 · Google Ads",
     "Which campaign had the best ROAS last month? Compare across platforms."),
    ("Meta Ads",
     "Show campaigns where frequency is above 3.5 — chart spend vs frequency."),
    ("Google Ads",
     "Which keywords have quality score below 5 and the highest spend?"),
    ("DV360",
     "List placements with viewability under 50% and their CPM."),
    ("All sources",
     "What is our total media spend this quarter broken down by platform? Show as a pie chart."),
    ("SA360 · GA4",
     "Compare CTR trend week over week for all search campaigns."),
]


def render_chat():
    uid = st.session_state["user"]["user_id"]

    if not st.session_state.get("azure_endpoint") or \
       not st.session_state.get("azure_api_key"):
        st.markdown("""
        <div class="welcome-area">
            <div class="w-logo">Campaign<span>IQ</span></div>
            <div class="w-sub">
                Configure your Azure OpenAI credentials in
                <strong>🔑 API Configuration</strong> on the left to get started.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Anomaly banner (show when data is loaded, once per session)
    if get_uploads(uid) and not st.session_state.get("anomalies_shown"):
        anomalies = run_anomaly_checks(uid)
        if anomalies:
            with st.expander(
                f"⚠️ {len(anomalies)} anomaly alert(s) detected across your data",
                expanded=True
            ):
                for a in anomalies:
                    st.markdown(
                        f'<div class="anomaly-banner">{a}</div>',
                        unsafe_allow_html=True
                    )
        st.session_state["anomalies_shown"] = True

    messages = st.session_state.get("messages", [])

    # Welcome state
    if not messages:
        uploads = get_uploads(uid)
        if not uploads:
            st.markdown("""
            <div class="welcome-area">
                <div class="w-logo">Campaign<span>IQ</span></div>
                <div class="w-sub">
                    Upload your campaign exports (SA360, Google Ads, Meta, DV360, GA4)
                    from the sidebar. The source is auto-detected from column headers —
                    no configuration needed.
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="welcome-area">
                <div class="w-logo">Campaign<span>IQ</span></div>
                <div class="w-sub">
                    Ask anything about your campaign data — performance, spend,
                    trends, anomalies, cross-platform comparisons, or charts.
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="prompt-grid">', unsafe_allow_html=True)
            for src_label, prompt_text in EXAMPLE_PROMPTS:
                st.markdown(
                    f'<div class="prompt-chip">'
                    f'<span class="pc-src">{src_label}</span>'
                    f'{prompt_text}'
                    f'</div>',
                    unsafe_allow_html=True
                )
            st.markdown('</div>', unsafe_allow_html=True)

    # Render conversation history
    for msg in messages:
        role   = msg["role"]
        avatar = "👤" if role == "user" else "📊"
        with st.chat_message(role, avatar=avatar):
            st.markdown(msg["content"])
            if msg.get("chart_key") and \
               msg["chart_key"] in st.session_state.get("charts", {}):
                st.pyplot(st.session_state["charts"][msg["chart_key"]])
            if msg.get("tool_used"):
                st.markdown(
                    f'<div class="tool-badge">'
                    f'<span class="tb-dot"></span>{msg["tool_used"]}</div>',
                    unsafe_allow_html=True
                )

    # Chat input
    prompt = st.chat_input(
        "Ask about your campaigns — performance, spend, trends, anomalies…",
        key="chat_input"
    )

    if prompt:
        user = st.session_state["user"]

        # Create or reuse conversation
        if not st.session_state.get("current_conv"):
            cid = create_conversation(user["user_id"], generate_title(prompt))
            st.session_state["current_conv"] = cid
        else:
            cid = st.session_state["current_conv"]

        # Save & show user message
        save_message(cid, "user", prompt)
        st.session_state.setdefault("messages", []).append(
            {"role": "user", "content": prompt,
             "tool_used": None, "chart_key": None}
        )
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # Run insight query
        with st.chat_message("assistant", avatar="📊"):
            with st.spinner("Analysing your campaign data…"):
                answer, fig, sql_used, tool_tag = run_insight_query(
                    prompt, user["user_id"]
                )

            st.markdown(answer)

            chart_key = None
            if fig is not None:
                chart_key = f"chart_{uuid.uuid4().hex[:8]}"
                st.session_state.setdefault("charts", {})[chart_key] = fig
                st.pyplot(fig)

            if tool_tag:
                st.markdown(
                    f'<div class="tool-badge">'
                    f'<span class="tb-dot"></span>{tool_tag}</div>',
                    unsafe_allow_html=True
                )

        save_message(cid, "assistant", answer, tool_used=tool_tag)
        st.session_state["messages"].append({
            "role": "assistant",
            "content": answer,
            "tool_used": tool_tag,
            "chart_key": chart_key,
        })


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

def main():
    init_database()
    seed_defaults()

    if not st.session_state.get("authenticated"):
        render_login()
    else:
        render_sidebar()
        render_chat()


if __name__ == "__main__":
    main()
