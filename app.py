
import streamlit as st
import pandas as pd
from open_ai_connection_api import ai_client 
import random

st.set_page_config(page_title="STAR Journal App", layout="wide")

# Load question CSV
def load_questions(path="star_questions.csv"):
    try:
        df = pd.read_csv(path)
        return df["question"].dropna().tolist()
    except Exception as e:
        st.error(f"Failed to load questions: {e}")
        return []

def generate_response_from_star_input(s, t, a, r, question=None):
    prompt = ""
    if question:
        prompt += f"Question: {question}\n"
    prompt += f"S: {s}\nT: {t}\nA: {a}\nR: {r}"
    messages = [{"role": "user", "content": f"Please rewrite the following STAR-format answer in more concise and natural English:\n\n{prompt}"}]
    return ai_client.analyze_text(messages)

def generate_interview_question(job_posting_text):
    prompt = f"Based on the following job posting, generate one behavioral interview question that can be answered using the STAR format:\n\n{job_posting_text}"
    messages = [{"role": "user", "content": prompt}]
    return ai_client.analyze_text(messages)

st.markdown(
    """
    <style>
    .stTextArea textarea {
        font-size: 20px !important;
    }
    
    .stMarkdown p {
        font-size: 18px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Tabs for three modes
tab1, tab2, tab3 = st.tabs(["📝 Diary", "🎯 General Questions", "💼 Interview Questions"])

# === Diary Tab ===
with tab1:
    st.header("Daily STAR Diary")
    with st.form("diary_form"):
        s = st.text_area("S - Situation")
        t = st.text_area("T - Task")
        a = st.text_area("A - Action")
        r = st.text_area("R - Result")
        submitted = st.form_submit_button("Submit")

    if submitted:
        try:
            result = generate_response_from_star_input(s, t, a, r)
            st.subheader("Rewritten Response:")
            st.write(result)
        except Exception as e:
            st.error(f"Error: {e}")

# === General Questions Tab ===
with tab2:
    st.header("General STAR Questions")
    questions = load_questions()
    if st.button("🎲 Get Random Question"):
        st.session_state["random_question"] = random.choice(questions)

    if "random_question" in st.session_state:
        st.subheader("Question:")
        st.write(st.session_state["random_question"])

        with st.form("general_form"):
            s = st.text_area("S - Situation", key="g_s")
            t = st.text_area("T - Task", key="g_t")
            a = st.text_area("A - Action", key="g_a")
            r = st.text_area("R - Result", key="g_r")
            general_submitted = st.form_submit_button("Submit")

        if general_submitted:
            try:
                result = generate_response_from_star_input(s, t, a, r, question=st.session_state["random_question"])
                st.subheader("Rewritten Response:")
                st.write(result)
            except Exception as e:
                st.error(f"Error: {e}")

# === Interview Questions Tab ===
with tab3:
    st.header("Interview Preparation")
    job_posting_text = st.text_area("Paste the Job Posting Here")

    if st.button("✨ Generate Interview Question"):
        if job_posting_text.strip():
            try:
                st.session_state["interview_question"] = generate_interview_question(job_posting_text)
            except Exception as e:
                st.error(f"Error generating question: {e}")
        else:
            st.warning("Please paste a job posting first.")

    if "interview_question" in st.session_state:
        st.subheader("Generated Interview Question:")
        st.write(st.session_state["interview_question"])

        with st.form("interview_form"):
            s = st.text_area("S - Situation", key="i_s")
            t = st.text_area("T - Task", key="i_t")
            a = st.text_area("A - Action", key="i_a")
            r = st.text_area("R - Result", key="i_r")
            interview_submitted = st.form_submit_button("Submit")

        if interview_submitted:
            try:
                result = generate_response_from_star_input(s, t, a, r, question=st.session_state["interview_question"])
                st.subheader("Rewritten Response:")
                st.write(result)
            except Exception as e:
                st.error(f"Error: {e}")
