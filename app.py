
import streamlit as st
import pandas as pd
from open_ai_connection_api import ai_client
import random

st.set_page_config(page_title="STAR Journal App", layout="wide")

# --- Session State Initialization ---
for key in ["diary_input", "general_input", "interview_input", "interview_questions", "interview_index"]:
    if key not in st.session_state:
        if key == "interview_questions":
            st.session_state[key] = []
        elif key == "interview_index":
            st.session_state[key] = 0
        else:
            st.session_state[key] = ""

# Inject dark theme and styling
st.markdown("""
    <style>
    body {
        background-color: #1e1e1e;
        color: #f5f5f5;
    }
    .stApp {
        background-color: #1e1e1e;
    }
    .stTextArea textarea {
        background-color: #2e2e2e;
        color: #ffffff;
        font-size: 20px !important;
    }
    .stMarkdown p {
        font-size: 18px !important;
        color: #f5f5f5;
    }
    .stButton button {
        background-color: #333333;
        color: #ffffff;
        border: none;
    }
    .stButton button:hover {
        background-color: #555555;
    }
    </style>
""", unsafe_allow_html=True)

# Load general questions from CSV
def load_questions(path="star_questions.csv"):
    try:
        df = pd.read_csv(path)
        return df["question"].dropna().tolist()
    except Exception as e:
        st.error(f"Failed to load questions: {e}")
        return []

def generate_response_from_input(text, question=None):
    prompt = ""
    if question:
        prompt += f"Question: {question}\n"
    prompt += f"Answer: {text}"
    messages = [{"role": "user", "content": f"Please rewrite the following STAR-format answer in more concise and natural English:\n\n{prompt}"}]
    return ai_client.analyze_text(messages)

def generate_simple_interview_questions(jd_text, save_path="interview_questions.csv"):
    prompt = (
        f"Generate 50 simple and clear behavioral interview questions based on the following job description. "
        f"Each question should be answerable using the STAR format. List them clearly in bullet points.\n\n{jd_text}"
    )
    messages = [{"role": "user", "content": prompt}]
    result = ai_client.analyze_text(messages)
    question_list = [q.strip("- ").strip() for q in result.split("\n") if q.strip()]
    pd.DataFrame({"question": question_list}).to_csv(save_path, index=False)
    return question_list

# Tabs
tab1, tab2, tab3 = st.tabs(["📝 Diary", "🎯 General Questions", "💼 Interview Questions"])

# === Diary Tab ===
with tab1:
    st.header("Daily STAR Diary")
    diary_input = st.text_area("Write about your day in STAR format:", value=st.session_state.diary_input, key="diary_textarea")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Submit", key="diary_submit"):
            try:
                result = generate_response_from_input(diary_input)
                st.session_state.diary_input = diary_input
                st.subheader("Rewritten Response:")
                st.write(result)
            except Exception as e:
                st.error(f"Error: {e}")
    with col2:
        if st.button("Clear", key="clear_diary"):
            st.session_state.diary_input = ""
            st.experimental_rerun()

# === General Questions Tab ===
with tab2:
    st.header("General STAR Questions")
    questions = load_questions()
    if st.button("🎲 Get Random Question"):
        st.session_state["random_question"] = random.choice(questions)
        st.session_state.general_input = ""

    if "random_question" in st.session_state:
        st.subheader("Question:")
        st.write(st.session_state["random_question"])

        general_input = st.text_area("Answer the question in STAR format:", value=st.session_state.general_input, key="general_textarea")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Submit", key="general_submit"):
                try:
                    result = generate_response_from_input(general_input, question=st.session_state["random_question"])
                    st.session_state.general_input = general_input
                    st.subheader("Rewritten Response:")
                    st.write(result)
                except Exception as e:
                    st.error(f"Error: {e}")
        with col2:
            if st.button("Clear", key="clear_general"):
                st.session_state.general_input = ""
                st.experimental_rerun()

# === Interview Questions Tab ===
with tab3:
    st.header("Interview Preparation")
    uploaded_jd = st.file_uploader("Upload Job Description (TXT)", type=["txt"])
    if uploaded_jd and st.button("Generate CSV of Interview Questions"):
        jd_text = uploaded_jd.read().decode("utf-8")
        questions = generate_simple_interview_questions(jd_text)
        st.session_state.interview_questions = questions
        st.session_state.interview_index = 0
        st.session_state.interview_input = ""
        st.success("Interview questions generated and saved to CSV.")

    if st.session_state.interview_questions:
        index = st.session_state.interview_index
        current_question = st.session_state.interview_questions[index]

        st.subheader("Interview Question:")
        st.write(current_question)

        interview_input = st.text_area("Answer the question in STAR format:", value=st.session_state.interview_input, key="interview_textarea")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Submit", key="interview_submit"):
                try:
                    result = generate_response_from_input(interview_input, question=current_question)
                    st.session_state.interview_input = interview_input
                    st.subheader("Rewritten Response:")
                    st.write(result)
                except Exception as e:
                    st.error(f"Error: {e}")
        with col2:
            if st.button("Clear", key="clear_interview"):
                st.session_state.interview_input = ""
                st.experimental_rerun()

        if st.button("Next Question"):
            st.session_state.interview_index = (index + 1) % len(st.session_state.interview_questions)
            st.session_state.interview_input = ""
            st.experimental_rerun()
