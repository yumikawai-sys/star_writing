import streamlit as st
import pandas as pd
import random
import os
from open_ai_connection_api import ai_client

st.set_page_config(page_title="STAR Journal App", layout="wide")

# Initialize session state
for key in ["diary_input", "general_input", "interview_input", "interview_questions", "interview_index"]:
    if key not in st.session_state:
        st.session_state[key] = "" if "input" in key else ([] if "questions" in key else 0)

# Apply custom styling
st.markdown("""
    <style>
    body {
        background-color: #1e1e1e;
        color: #f5f5f5;
    }
    .stApp {
        background-color: #1e1e1e;
    }
    h1, h2, h3 {
        color: white !important;
    }
    .stTextArea textarea {
        background-color: #2e2e2e;
        color: white;
        font-size: 20px !important;
    }
    .stMarkdown p, .stText, div[data-testid="stMarkdownContainer"] {
        color: white !important;
        font-size: 20px !important;
    }
    .stButton button {
        background-color: #333333;
        color: white;
    }
    .stButton button:hover {
        background-color: #555555;
    }
    div[data-baseweb="tab"] button {
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# OpenAI Response Handler
def generate_response_from_input(text, question=None):
    prompt = f"Question: {question}\nAnswer: {text}" if question else text
    messages = [{"role": "user", "content": f"Please rewrite the following STAR-format answer in more concise and natural English:\n\n{prompt}"}]
    return ai_client.analyze_text(messages)

# Interview Question Generator
def generate_simple_interview_questions(jd_text, save_path="interview_questions.csv"):
    prompt = (
        "Generate simple behavioral interview questions based on the following job description. "
        "Each question must be one sentence and end with a question mark. Output one per line with no bullets or numbers.\n\n" + jd_text
    )
    messages = [{"role": "user", "content": prompt}]
    response = ai_client.analyze_text(messages)
    questions = [q.strip() for q in response.split("\n") if len(q.strip().split()) > 4 and '?' in q]
    df = pd.DataFrame({"question": questions})
    df.to_csv(save_path, index=False)
    return questions

# Load and combine job-specific + general questions
def load_combined_interview_questions():
    all_questions = []

    if os.path.exists("interview_questions.csv"):
        df1 = pd.read_csv("interview_questions.csv")
        all_questions += df1["question"].dropna().tolist()

    if os.path.exists("general_interview_questions.csv"):
        df2 = pd.read_csv("general_interview_questions.csv")
        all_questions += df2["question"].dropna().tolist()

    return all_questions

# Tabs
tab1, tab2, tab3 = st.tabs(["📝 Diary", "🎯 General Questions", "💼 Interview Questions"])

# === Diary Tab ===
with tab1:
    st.header("Daily STAR Diary")
    diary_input = st.text_area("Write about your day in STAR format:", value=st.session_state.diary_input, key="diary_textarea")
    col1, col2 = st.columns([5, 1])
    with col1:
        if st.button("Submit", key="diary_submit"):
            result = generate_response_from_input(diary_input)
            st.session_state.diary_input = diary_input
            st.subheader("Rewritten Response:")
            st.write(result)
    with col2:
        if st.button("Clear", key="clear_diary"):
            st.session_state.diary_input = ""
            st.rerun()

# === General Questions Tab ===
with tab2:
    st.header("General STAR Questions")
    try:
        df = pd.read_csv("star_questions.csv")
        questions = df["question"].dropna().tolist()
    except:
        questions = []

    if st.button("🎲 Get Random Question"):
        st.session_state["random_question"] = random.choice(questions)
        st.session_state.general_input = ""

    if "random_question" in st.session_state and st.session_state["random_question"]:
        st.subheader("Question:")
        st.write(st.session_state["random_question"])

        general_input = st.text_area("Answer the question in STAR format:", value=st.session_state.general_input, key="general_textarea")
        col1, col2 = st.columns([5, 1])
        with col1:
            if st.button("Submit", key="general_submit"):
                result = generate_response_from_input(general_input, question=st.session_state["random_question"])
                st.session_state.general_input = general_input
                st.subheader("Rewritten Response:")
                st.write(result)
        with col2:
            if st.button("Clear", key="clear_general"):
                st.session_state.general_input = ""
                st.rerun()

# === Interview Tab ===
with tab3:
    st.header("Interview Preparation")
    uploaded_jd = st.file_uploader("Upload Job Description (TXT)", type=["txt"])

    if uploaded_jd and st.button("Generate CSV of Interview Questions"):
        jd_text = uploaded_jd.read().decode("utf-8")
        job_specific_questions = generate_simple_interview_questions(jd_text)
        combined_questions = job_specific_questions + load_combined_interview_questions()
        random.shuffle(combined_questions)

        st.session_state.interview_questions = combined_questions
        st.session_state.interview_index = 0
        st.session_state.interview_input = ""
        st.success("Interview questions generated and mixed with general questions.")

    if st.session_state.interview_questions:
        q_index = st.session_state.interview_index
        current_question = st.session_state.interview_questions[q_index]

        st.subheader("Interview Question:")
        st.write(current_question)

        interview_input = st.text_area("Answer the question in STAR format:", value=st.session_state.interview_input, key="interview_textarea")
        col1, col2 = st.columns([5, 1])
        with col1:
            if st.button("Submit", key="interview_submit"):
                result = generate_response_from_input(interview_input, question=current_question)
                st.session_state.interview_input = interview_input
                st.subheader("Rewritten Response:")
                st.write(result)
        with col2:
            if st.button("Clear", key="clear_interview"):
                st.session_state.interview_input = ""
                st.rerun()

        if st.button("Next Question"):
            st.session_state.interview_index = (q_index + 1) % len(st.session_state.interview_questions)
            st.session_state.interview_input = ""
            st.rerun()
