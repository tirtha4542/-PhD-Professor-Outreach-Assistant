"""
Streamlit UI for the PhD Professor Outreach agent pipeline.

Run with:
    streamlit run streamlit_app.py

Place this file at your project root (alongside `src/`).
Requires TAVILY_API_KEY and your Mistral API key set as environment variables
(in a local .env for dev, or your host's env var settings in production).
"""

import json as _json
import os
import sys
import traceback

import streamlit as st

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.tools.resume_utils import extract_text_from_upload
from src.pipelines.pipeline import run_professor_outreach_pipeline

st.set_page_config(page_title="PhD Professor Outreach", page_icon="🎓", layout="wide")

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .hero {
        padding: 2rem 2rem 1.6rem 2rem;
        border-radius: 16px;
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 55%, #a855f7 100%);
        margin-bottom: 1.6rem;
    }
    .hero h1 {
        color: white;
        font-size: 2rem;
        margin-bottom: 0.3rem;
    }
    .hero p {
        color: rgba(255,255,255,0.9);
        font-size: 1rem;
        margin: 0;
    }
    .metric-card {
        background: rgba(127,127,127,0.08);
        border: 1px solid rgba(127,127,127,0.18);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        text-align: center;
    }
    .metric-card .value {
        font-size: 1.8rem;
        font-weight: 700;
    }
    .metric-card .label {
        font-size: 0.8rem;
        opacity: 0.7;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .prof-card {
        border: 1px solid rgba(127,127,127,0.2);
        border-radius: 14px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 0.9rem;
        background: rgba(127,127,127,0.04);
        transition: border-color 0.15s ease;
    }
    .prof-card:hover {
        border-color: rgba(124,58,237,0.55);
    }
    .prof-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    .prof-name {
        font-size: 1.1rem;
        font-weight: 700;
    }
    .prof-university {
        opacity: 0.75;
        font-size: 0.92rem;
    }
    .badge {
        display: inline-block;
        padding: 0.22rem 0.65rem;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 700;
        white-space: nowrap;
    }
    .badge-high { background: rgba(34,197,94,0.18); color: #22c55e; }
    .badge-mid  { background: rgba(234,179,8,0.18); color: #eab308; }
    .badge-low  { background: rgba(239,68,68,0.18); color: #ef4444; }
    .pill {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 8px;
        background: rgba(99,102,241,0.14);
        color: #818cf8;
        font-size: 0.82rem;
        margin: 0.15rem 0.3rem 0.15rem 0;
    }
    .section-title {
        font-size: 1.25rem;
        font-weight: 700;
        margin: 1.4rem 0 0.6rem 0;
    }
</style>
""", unsafe_allow_html=True)


def init_state():
    defaults = {"pipeline_state": {}, "is_running": False}
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()

# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------
st.markdown("""
<div class="hero">
    <h1>🎓 PhD Professor Outreach Assistant</h1>
    <p>Upload your resume, pick a country, and let AI agents find, rank, and draft outreach emails to professors who match your research background.</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Input row
# ---------------------------------------------------------------------------
col1, col2 = st.columns([2, 1])
with col1:
    resume_file = st.file_uploader(
        "📄 Upload your resume",
        type=["pdf", "docx", "txt"],
        help="PDF, DOCX, or TXT",
    )
with col2:
    country = st.text_input("🌍 Target country", placeholder="e.g. USA")

run_clicked = st.button(
    "✨ Find professors",
    type="primary",
    use_container_width=True,
    disabled=st.session_state["is_running"] or not resume_file or not country.strip(),
)

st.divider()


def run_pipeline_ui(resume_file, country: str):
    st.session_state["is_running"] = True
    try:
        with st.status("Reading resume…", expanded=True) as status:
            resume_text = extract_text_from_upload(resume_file.getvalue(), resume_file.name)
            status.update(label="🔎 Running agent pipeline…", state="running")
            st.write(
                "**Parsing resume → searching professors → scraping faculty pages → "
                "ranking fit → drafting emails.** Watch your terminal for step-by-step logs — "
                "this can take a couple of minutes."
            )
            state = run_professor_outreach_pipeline(resume_text, country)
            status.update(label="✅ Pipeline complete", state="complete")
    except Exception:
        st.error("Pipeline raised an exception — see full traceback below.")
        st.code(traceback.format_exc())
        st.session_state["is_running"] = False
        return None

    st.session_state["is_running"] = False
    return state


if run_clicked:
    result_state = run_pipeline_ui(resume_file, country.strip())
    if result_state is not None:
        st.session_state["pipeline_state"] = result_state
        st.balloons()
        st.rerun()

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
state = st.session_state["pipeline_state"]


def fit_badge(score):
    if score is None:
        return ""
    score = int(score)
    cls = "badge-high" if score >= 7 else "badge-mid" if score >= 4 else "badge-low"
    return f'<span class="badge {cls}">Fit {score}/10</span>'


if state:
    profile = state.get("profile", {})
    professors = state.get("professors", [])

    # --- Metrics row ---
    scores = [p.get("fit_score") for p in professors if p.get("fit_score") is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else "—"
    with_email = sum(1 for p in professors if p.get("email"))

    m1, m2, m3, m4 = st.columns(4)
    for col, value, label in [
        (m1, len(professors), "Professors found"),
        (m2, avg_score, "Avg. fit score"),
        (m3, with_email, "With email found"),
        (m4, len(profile.get("research_interests", [])), "Research interests"),
    ]:
        with col:
            st.markdown(
                f'<div class="metric-card"><div class="value">{value}</div>'
                f'<div class="label">{label}</div></div>',
                unsafe_allow_html=True,
            )

    # --- Profile section ---
    st.markdown('<div class="section-title">🧑‍🎓 Your profile</div>', unsafe_allow_html=True)
    pcol1, pcol2 = st.columns(2)
    with pcol1:
        st.markdown(f"**Name:** {profile.get('name') or '—'}")
        st.markdown(f"**Degree:** {profile.get('degree') or '—'}")
        interests = profile.get("research_interests", [])
        if interests:
            st.markdown(
                "".join(f'<span class="pill">{i}</span>' for i in interests),
                unsafe_allow_html=True,
            )
    with pcol2:
        skills = profile.get("skills", [])
        if skills:
            st.markdown(
                "**Skills:** " + "".join(f'<span class="pill">{s}</span>' for s in skills),
                unsafe_allow_html=True,
            )
        pubs = profile.get("publications") or []
        st.markdown(f"**Publications:** {', '.join(pubs) if pubs else '—'}")
    if profile.get("summary"):
        st.caption(profile["summary"])

    # --- Professors section ---
    st.markdown(f'<div class="section-title">👨‍🏫 Matched professors ({len(professors)})</div>', unsafe_allow_html=True)

    if not professors:
        st.info("No professors were matched. Try a broader set of research interests or a different country.")
    else:
        sort_choice = st.selectbox("Sort by", ["Fit score (high to low)", "University name"], label_visibility="collapsed")
        if sort_choice == "University name":
            professors = sorted(professors, key=lambda p: (p.get("university") or "").lower())
        else:
            professors = sorted(professors, key=lambda p: p.get("fit_score") or 0, reverse=True)

        for i, prof in enumerate(professors):
            st.markdown(
                f"""
                <div class="prof-card">
                    <div class="prof-header">
                        <div>
                            <span class="prof-name">{prof.get('name', 'Unknown')}</span><br>
                            <span class="prof-university">{prof.get('university') or '—'}</span>
                        </div>
                        {fit_badge(prof.get('fit_score'))}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander("Details & email draft", expanded=False):
                dcol1, dcol2 = st.columns(2)
                with dcol1:
                    st.markdown(f"**📧 Email:** {prof.get('email') or 'not found'}")
                    st.markdown(f"**🔬 Research area:** {prof.get('research_area') or '—'}")
                with dcol2:
                    st.markdown(f"**🎯 Fit reason:** {prof.get('fit_reason') or '—'}")
                    if prof.get("profile_url"):
                        st.markdown(f"**🔗 Profile:** [{prof['profile_url']}]({prof['profile_url']})")

                if prof.get("email_draft"):
                    st.markdown("---")
                    st.markdown("**✉️ Draft outreach email**")
                    st.text_area(
                        "Email draft",
                        value=prof["email_draft"],
                        height=220,
                        key=f"draft_{i}",
                        label_visibility="collapsed",
                    )

        st.divider()
        st.download_button(
            "⬇️ Download all results (.json)",
            data=_json.dumps(state, indent=2),
            file_name="professor_matches.json",
            mime="application/json",
            use_container_width=True,
        )
else:
    st.info("👆 Upload your resume and enter a target country, then click **Find professors**.")