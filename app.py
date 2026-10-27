import csv
import io
import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from streamlit_autorefresh import st_autorefresh

APP_DIR = Path(__file__).resolve().parent
QUESTION_FILE = APP_DIR / "questions.json"
QUESTIONS = json.loads(QUESTION_FILE.read_text(encoding="utf-8"))
LETTERS = ["A", "B", "C", "D"]

st.set_page_config(page_title="Operating Systems Online Test", page_icon="🧠", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2.5rem; max-width: 1100px;}
.hero {padding: 1.25rem 1.5rem; border-radius: 16px; background: linear-gradient(120deg,#0d3157,#245c86); color: white; margin-bottom: 1rem;}
.hero h1 {color:white; margin-bottom:.25rem;}
.small-muted {color:#5f6b7a; font-size:.9rem;}
.question-card {border:1px solid rgba(120,130,145,.3); border-radius:14px; padding:1rem 1.1rem; margin: .5rem 0 1rem 0;}
.metric-card {border:1px solid rgba(120,130,145,.28); border-radius:12px; padding:.75rem 1rem;}
</style>
<div class="hero"><h1>Operating Systems — Online Assessment</h1><div>UE25CS242A · Reasoning MCQ practice · Units 1, 2 and 3</div></div>
""", unsafe_allow_html=True)

@st.cache_data
def load_qs():
    return QUESTIONS


@st.cache_resource
def get_backend_client():
    """Create a server-side Supabase client only when credentials are configured."""
    try:
        if "supabase" not in st.secrets:
            return None, "Supabase storage is not configured. Students can still complete the test and download their result."
        cfg = st.secrets["supabase"]
        url = str(cfg.get("url", "")).strip()
        key = str(cfg.get("service_role_key", "")).strip()
        if not url or not key or "YOUR_" in url or "YOUR_" in key:
            return None, "Supabase storage is not configured. Students can still complete the test and download their result."
        from supabase import create_client
        return create_client(url, key), "Supabase storage is configured."
    except Exception as exc:
        return None, f"Supabase storage is unavailable: {exc}"


def current_backend_status():
    client, message = get_backend_client()
    return client, message


def start_attempt(name, srn, scope, minutes, shuffle):
    selected = [q for q in load_qs() if scope == "Full Test (Units 1 + 2 + 3)" or q["unit"] == scope]
    if shuffle:
        random.Random(time.time_ns()).shuffle(selected)
    st.session_state.attempt_questions = [q["id"] for q in selected]
    st.session_state.student_name = name.strip()
    st.session_state.student_srn = srn.strip().upper()
    st.session_state.test_scope = scope
    st.session_state.duration_seconds = int(minutes) * 60
    st.session_state.started_epoch = time.time()
    st.session_state.started_iso = datetime.now(timezone.utc).isoformat()
    st.session_state.answers = {}
    st.session_state.reviewed = set()
    st.session_state.current_index = 0
    st.session_state.attempt_active = True
    st.session_state.attempt_result = None
    st.session_state.db_save_status = None


def make_result(auto_submitted=False):
    q_by_id = {q["id"]: q for q in load_qs()}
    attempt_qs = [q_by_id[qid] for qid in st.session_state.attempt_questions]
    answers = st.session_state.get("answers", {})
    reviewed = st.session_state.get("reviewed", set())
    details = []
    score = 0
    for q in attempt_qs:
        chosen = answers.get(q["id"])
        correct = chosen == q["answer"]
        score += int(correct)
        details.append({
            "question_id": q["id"], "unit": q["unit"], "number": q["number"],
            "topic": q["topic"], "question": q["question"],
            "selected_option": chosen,
            "selected_answer": q["options"].get(chosen, "Not answered") if chosen else "Not answered",
            "correct_option": q["answer"], "correct_answer": q["options"][q["answer"]],
            "is_correct": correct, "explanation": q["explanation"],
            "marked_for_review": q["id"] in reviewed
        })
    total = len(attempt_qs)
    end_epoch = time.time()
    return {
        "student_name": st.session_state.student_name,
        "srn": st.session_state.student_srn,
        "test_scope": st.session_state.test_scope,
        "score": score,
        "total_questions": total,
        "unanswered": sum(1 for q in attempt_qs if not answers.get(q["id"])),
        "percentage": round(score * 100 / total, 2) if total else 0,
        "started_at": st.session_state.started_iso,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": max(0, int(end_epoch - st.session_state.started_epoch)),
        "auto_submitted": auto_submitted,
        "answers_json": {qid: ans for qid, ans in answers.items() if qid in st.session_state.attempt_questions},
        "review_json": details,
    }


def persist_result(result):
    client, message = current_backend_status()
    if client is None:
        st.session_state.db_save_status = message
        return
    try:
        row = {k: result[k] for k in [
            "student_name", "srn", "test_scope", "score", "total_questions", "percentage",
            "started_at", "submitted_at", "elapsed_seconds", "answers_json", "review_json"
        ]}
        row["auto_submitted"] = result["auto_submitted"]
        client.table("os_online_test_results").insert(row).execute()
        st.session_state.db_save_status = "Submission saved to the instructor results database."
    except Exception as exc:
        st.session_state.db_save_status = f"Result could not be saved to the central database: {exc}. Download the result file as a backup."


def submit_attempt(auto_submitted=False):
    if st.session_state.get("attempt_result") is not None:
        return
    result = make_result(auto_submitted=auto_submitted)
    st.session_state.attempt_result = result
    st.session_state.attempt_active = False
    persist_result(result)


def result_csv(result):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["student_name", "srn", "test_scope", "score", "total_questions", "unanswered", "percentage", "started_at", "submitted_at", "elapsed_seconds", "auto_submitted"])
    writer.writeheader()
    writer.writerow({k: result.get(k) for k in writer.fieldnames})
    return buf.getvalue().encode("utf-8-sig")


def show_result(result):
    st.success("Test submitted. Your result is displayed below.")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Score", f"{result['score']} / {result['total_questions']}")
    col2.metric("Percentage", f"{result['percentage']:.2f}%")
    col3.metric("Unanswered", result["unanswered"])
    col4.metric("Time used", f"{result['elapsed_seconds']//60}m {result['elapsed_seconds']%60}s")
    if result.get("auto_submitted"):
        st.warning("The time limit expired, so the test was submitted automatically.")
    if st.session_state.get("db_save_status"):
        if "saved" in st.session_state.db_save_status.lower():
            st.info(st.session_state.db_save_status)
        else:
            st.warning(st.session_state.db_save_status)
    srn_safe = "".join(ch for ch in result["srn"] if ch.isalnum() or ch in "-_ ").strip().replace(" ", "_") or "student"
    c1, c2 = st.columns(2)
    c1.download_button("Download result summary (CSV)", result_csv(result), file_name=f"OS_test_result_{srn_safe}.csv", mime="text/csv", use_container_width=True)
    c2.download_button("Download detailed answers (JSON)", json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"), file_name=f"OS_test_details_{srn_safe}.json", mime="application/json", use_container_width=True)
    st.subheader("Question-wise review")
    st.caption("Correct answers and explanations are visible after submission.")
    for idx, item in enumerate(result["review_json"], start=1):
        status = "✅" if item["is_correct"] else ("⬜" if item["selected_option"] is None else "❌")
        label = f"{status} Q{idx} · {item['unit']} · {item['topic']}"
        with st.expander(label):
            st.write(item["question"])
            st.write(f"**Your answer:** {item['selected_option'] + '. ' if item['selected_option'] else ''}{item['selected_answer']}")
            st.write(f"**Correct answer:** {item['correct_option']}. {item['correct_answer']}")
            st.write(f"**Explanation:** {item['explanation']}")


def instructor_dashboard():
    st.header("Instructor dashboard")
    try:
        password_expected = str(st.secrets.get("app", {}).get("admin_password", "")).strip()
    except Exception:
        password_expected = ""
    if not password_expected or "CHANGE_ME" in password_expected:
        st.warning("Set [app].admin_password in Streamlit Secrets before using the instructor dashboard.")
        return
    password = st.text_input("Instructor password", type="password", key="dashboard_password")
    if not password:
        st.info("Enter the instructor password to view submissions.")
        return
    if password != password_expected:
        st.error("Password does not match.")
        return
    client, message = current_backend_status()
    if client is None:
        st.warning("Central results storage is not connected. Submissions completed on individual devices cannot be retrieved here without Supabase.")
        return
    try:
        resp = client.table("os_online_test_results").select("id,student_name,srn,test_scope,score,total_questions,percentage,started_at,submitted_at,elapsed_seconds,auto_submitted").order("submitted_at", desc=True).limit(2000).execute()
        rows = resp.data or []
    except Exception as exc:
        st.error(f"Could not retrieve results: {exc}")
        return
    if not rows:
        st.info("No submitted attempts are in the database yet.")
        return
    import pandas as pd
    df = pd.DataFrame(rows)
    st.metric("Submissions retrieved", len(df))
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("Download all retrieved results (CSV)", df.to_csv(index=False).encode("utf-8-sig"), file_name="OS_online_test_all_results.csv", mime="text/csv")


with st.sidebar:
    st.subheader("Assessment controls")
    mode = st.radio("Open", ["Student test", "Instructor results"], index=0)
    st.divider()
    st.caption("90 original practice MCQs · 30 per unit")
    st.caption("One mark per correct answer; no negative marking.")

if mode == "Instructor results":
    instructor_dashboard()
    st.stop()

# Attempt has already been submitted
if st.session_state.get("attempt_result") is not None:
    show_result(st.session_state.attempt_result)
    if st.button("Start a new attempt", type="secondary"):
        for key in ["attempt_questions", "student_name", "student_srn", "test_scope", "duration_seconds", "started_epoch", "started_iso", "answers", "reviewed", "current_index", "attempt_active", "attempt_result", "db_save_status"]:
            st.session_state.pop(key, None)
        st.rerun()
    st.stop()

# Configuration/start screen
if not st.session_state.get("attempt_active"):
    st.subheader("Student details and test setup")
    with st.form("start_test_form"):
        col1, col2 = st.columns(2)
        with col1:
            student_name = st.text_input("Student name", max_chars=100)
        with col2:
            srn = st.text_input("SRN / Register number", max_chars=40)
        scope = st.selectbox("Choose question set", ["Full Test (Units 1 + 2 + 3)", "Unit 1", "Unit 2", "Unit 3"], index=0)
        duration_label = st.selectbox("Time limit", ["15 minutes", "30 minutes", "45 minutes", "60 minutes", "90 minutes", "120 minutes"], index=2)
        shuffle = st.checkbox("Shuffle question order for this attempt", value=True)
        agree = st.checkbox("I confirm that I am ready to begin. The timer starts immediately.", value=False)
        start = st.form_submit_button("Start online test", type="primary", use_container_width=True)
    if start:
        if not student_name.strip() or not srn.strip():
            st.error("Enter both your name and SRN/register number.")
        elif not agree:
            st.error("Please confirm that you are ready to begin.")
        else:
            start_attempt(student_name, srn, scope, int(duration_label.split()[0]), shuffle)
            st.rerun()
    st.markdown("### Test instructions")
    st.markdown("""
    - Select **Full Test** for all 45 questions, or choose one unit for a 15-question test.
    - Each question carries **1 mark**. There is **no negative marking**.
    - Navigate using **Previous** and **Next**. Your selections are retained during the attempt.
    - The test submits automatically when the timer expires.
    - Correct answers and explanations appear only after submission.
    - Central collection of results requires the instructor to configure Supabase. Without it, each student can download their own result files.
    """)
    st.stop()

# Active test
st_autorefresh(interval=1000, key="os_test_timer_refresh")
by_id = {q["id"]: q for q in load_qs()}
qids = st.session_state.attempt_questions
qs = [by_id[qid] for qid in qids]
total = len(qs)
elapsed = int(time.time() - st.session_state.started_epoch)
remaining = max(0, st.session_state.duration_seconds - elapsed)
if remaining <= 0:
    submit_attempt(auto_submitted=True)
    st.rerun()

answered = sum(1 for q in qs if st.session_state.answers.get(q["id"]))
marked = sum(1 for q in qs if q["id"] in st.session_state.reviewed)
header1, header2, header3, header4 = st.columns(4)
header1.metric("Candidate", st.session_state.student_name)
header2.metric("Questions", total)
header3.metric("Answered", f"{answered}/{total}")
header4.metric("Time remaining", f"{remaining//60:02d}:{remaining%60:02d}")
st.progress(answered / total if total else 0)
st.caption(f"{st.session_state.test_scope}  ·  SRN: {st.session_state.student_srn}  ·  Marked for review: {marked}")

idx = max(0, min(st.session_state.current_index, total - 1))
q = qs[idx]
st.markdown(f"### Question {idx+1} of {total}")
st.markdown(f"**{q['unit']} · {q.get('question_type', 'Question')} · {q['difficulty']} · {q['topic']}**")
st.markdown(f"<div class='question-card'>{q['question']}</div>", unsafe_allow_html=True)
widget_key = f"choice_{q['id']}"
if widget_key not in st.session_state:
    st.session_state[widget_key] = st.session_state.answers.get(q["id"])
choice = st.radio("Choose one answer", options=LETTERS, format_func=lambda letter: f"{letter}. {q['options'][letter]}", index=None, key=widget_key)
if choice:
    st.session_state.answers[q["id"]] = choice
reviewed_value = st.checkbox("Mark this question for review", value=(q["id"] in st.session_state.reviewed), key=f"review_widget_{q['id']}")
if reviewed_value:
    st.session_state.reviewed.add(q["id"])
else:
    st.session_state.reviewed.discard(q["id"])

b1, b2, b3 = st.columns([1, 1, 2])
with b1:
    if st.button("← Previous", disabled=(idx == 0), use_container_width=True):
        st.session_state.current_index = idx - 1
        st.rerun()
with b2:
    if st.button("Next →", disabled=(idx >= total - 1), type="primary", use_container_width=True):
        st.session_state.current_index = idx + 1
        st.rerun()
with b3:
    if st.button("Submit test", type="secondary", use_container_width=True):
        submit_attempt(auto_submitted=False)
        st.rerun()

with st.expander("Question navigator", expanded=False):
    st.write("Select a number to jump directly to a question.")
    cols = st.columns(10)
    for n in range(total):
        qn = qs[n]
        has_answer = bool(st.session_state.answers.get(qn["id"]))
        is_marked = qn["id"] in st.session_state.reviewed
        label = f"{'✓' if has_answer else '·'}{'★' if is_marked else ''} {n+1}"
        if cols[n % 10].button(label, key=f"nav_{n}", use_container_width=True):
            st.session_state.current_index = n
            st.rerun()
