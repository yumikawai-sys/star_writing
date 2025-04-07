import streamlit as st
import pandas as pd
import random
import os
from open_ai_connection_api import ai_client  

st.set_page_config(page_title="STAR Journal App", layout="wide")

# Initialize session state
for key in [
    "interview_questions", "interview_index",
    "diary_input", "general_input", "interview_input",
    "diary_clear_trigger", "general_clear_trigger", "interview_clear_trigger",
    "random_question"
]:
    if key not in st.session_state:
        st.session_state[key] = "" if "input" in key or "question" in key else (
            True if "trigger" in key else ([] if "questions" in key else 0)
        )

# Styling
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

# === Utilities ===
def generate_response_from_input(text, question=None):
    prompt = f"Question: {question}\nAnswer: {text}" if question else text
    messages = [{"role": "user", "content": f"Please rewrite the following STAR-format answer in more concise and natural English:\n\n{prompt}"}]
    return ai_client.analyze_text(messages)

def generate_simple_interview_questions(jd_text, save_path="interview_questions.csv"):
    prompt = (
        "Generate simple behavioral interview questions based on the following job description. "
        "Each question must be one sentence and end with a question mark. Output one per line with no bullets or numbers.\n\n" + jd_text
    )
    messages = [{"role": "user", "content": prompt}]
    response = ai_client.analyze_text(messages)
    questions = [q.strip() for q in response.split("\n") if len(q.strip().split()) > 4 and '?' in q]
    pd.DataFrame({"question": questions}).to_csv(save_path, index=False)
    return questions

def load_combined_interview_questions():
    all_qs = []
    if os.path.exists("interview_questions.csv"):
        all_qs += pd.read_csv("interview_questions.csv")["question"].dropna().tolist()
    if os.path.exists("general_interview_questions.csv"):
        all_qs += pd.read_csv("general_interview_questions.csv")["question"].dropna().tolist()
    return all_qs

def read_saved_answers(path="answers.csv"):
    if os.path.exists(path):
        df = pd.read_csv(path)
        return dict(zip(df["question"], df["answer"]))
    return {}

def save_answer(question, answer, path="answers.csv"):
    data = read_saved_answers(path)
    data[question] = answer
    pd.DataFrame(data.items(), columns=["question", "answer"]).to_csv(path, index=False)

# === Tabs ===
tab1, tab2, tab3 = st.tabs(["📝 Diary", "🎯 General Questions", "💼 Interview Questions"])

# === Diary Tab ===
with tab1:
    st.header("Daily STAR Diary")

    diary_input = "" if st.session_state["diary_clear_trigger"] else st.session_state["diary_input"]
    diary_input = st.text_area("Write about your day in STAR format:", value=diary_input, key="diary_text")

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("Submit", key="submit_diary"):
            st.session_state["diary_input"] = diary_input
            st.session_state["diary_clear_trigger"] = False
            result = generate_response_from_input(diary_input)
            st.subheader("Rewritten Response:")
            st.write(result)
    with col2:
        if st.button("Clear Diary", key="clear_diary"):
            st.session_state["diary_clear_trigger"] = True
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
        st.session_state["general_clear_trigger"] = True
        st.rerun()

    if st.session_state["random_question"]:
        q = st.session_state["random_question"]
        st.subheader("Question:")
        st.write(q)

        general_input = "" if st.session_state["general_clear_trigger"] else st.session_state["general_input"]
        general_input = st.text_area("Answer the question in STAR format:", value=general_input, key="general_text")

        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("Submit", key="submit_general"):
                st.session_state["general_input"] = general_input
                st.session_state["general_clear_trigger"] = False
                answers = read_saved_answers()
                if q in answers:
                    st.subheader("Saved Response:")
                    st.write(answers[q])
                else:
                    result = generate_response_from_input(general_input, question=q)
                    save_answer(q, result)
                    st.subheader("Rewritten Response:")
                    st.write(result)
        with col2:
            if st.button("Clear General", key="clear_general"):
                st.session_state["general_clear_trigger"] = True
                st.rerun()

# === Interview Tab ===
with tab3:
    st.header("Interview Preparation")

    uploaded_jd = st.file_uploader("Upload Job Description (TXT)", type=["txt"])

    if uploaded_jd and st.button("Generate CSV of Interview Questions"):
        jd_text = uploaded_jd.read().decode("utf-8")
        job_qs = generate_simple_interview_questions(jd_text)
        combined = job_qs + load_combined_interview_questions()
        random.shuffle(combined)
        st.session_state["interview_questions"] = combined
        st.session_state["interview_index"] = 0
        st.session_state["interview_clear_trigger"] = True
        st.success("Interview questions generated and mixed with general questions.")
        st.rerun()

    if st.session_state["interview_questions"]:
        idx = st.session_state["interview_index"]
        q = st.session_state["interview_questions"][idx]

        st.subheader("Interview Question:")
        st.write(q)

        interview_input = "" if st.session_state["interview_clear_trigger"] else st.session_state["interview_input"]
        interview_input = st.text_area("Answer the question in STAR format:", value=interview_input, key="interview_text")

        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("Submit", key="submit_interview"):
                st.session_state["interview_input"] = interview_input
                st.session_state["interview_clear_trigger"] = False
                answers = read_saved_answers()
                if q in answers:
                    st.subheader("Saved Response:")
                    st.write(answers[q])
                else:
                    result = generate_response_from_input(interview_input, question=q)
                    save_answer(q, result)
                    st.subheader("Rewritten Response:")
                    st.write(result)
        with col2:
            if st.button("Clear Interview", key="clear_interview"):
                st.session_state["interview_clear_trigger"] = True
                st.rerun()

        if st.button("Next Question"):
            st.session_state["interview_index"] = (idx + 1) % len(st.session_state["interview_questions"])
            st.session_state["interview_clear_trigger"] = True
            st.rerun()
