import streamlit as st
from PyPDF2 import PdfReader

st.set_page_config(page_title="PDF2Quiz", layout="wide", page_icon="🧠")


# 1. Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "home"

if "uploaded_file" not in st.session_state:                         # Used later
    st.session_state.uploaded_file = None

if "selected_pages" not in st.session_state:                        # Used later
    st.session_state.selected_pages = []

if "current_question" not in st.session_state:                      # Used later
    st.session_state.current_question = 1

# --- CSS for left column ---
if st.session_state.page == "home":
    st.markdown("""
    <style>
    [data-testid="stHorizontalBlock"] > div:first-child {
        background-color: #d3d3d3; 
        border-radius: 10px;
    }    
    [data-testid="stHorizontalBlock"] > div:first-child > div {
        padding: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. Home Page
if st.session_state.page == "home":
    col1, col2 = st.columns([1, 3])
    with col1:
        mode = st.radio("Select Mode:", ["Practice Mode", "Exam Mode"])                         #variable mode
        difficulty = st.selectbox("Select Difficulty:", ["Easy", "Medium", "Difficult"])        #variable diffculty
        num_questions = st.selectbox("Number of Questions:", [10, 20, 30, 40, 50])              #variable num_question

    with col2:

        st.title("🧠PDF2Quiz - Turn notes into MCQs")
        st.text("Upload lecture notes (PDF,DOCX,PPT) and PDF2Quiz will create a generate MCQs QUiz.")
        st.subheader("Upload your file")

        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])                            #variable uploaded_file
        if uploaded_file:
            st.session_state.uploaded_file = uploaded_file
            reader = PdfReader(uploaded_file)                                                   #variable reader
            total_pages = len(reader.pages)                                                     #variable total_pages
            st.session_state.selected_pages = st.multiselect(
                "Select pages to generate quiz from:",
                options=list(range(1, total_pages + 1)),
                default=[1]
            )

    if st.button("Generate Questions"):
        if st.session_state.uploaded_file and st.session_state.selected_pages:
            st.session_state.page = "questions"
            st.session_state.current_question = 1

# 3. Questions Page
elif st.session_state.page == "questions":
    if st.button("← Back"):
        st.session_state.page = "home"

    st.title("Questions")

    questions = [
        {"question": "What is 2 + 2?", "options": ["3", "4", "5", "6"]},
        {"question": "Capital of France?", "options": ["London", "Berlin", "Paris", "Rome"]}
    ]

    # Initialize current question index
    if "current_question" not in st.session_state:
        st.session_state.current_question = 0

    q_idx = st.session_state.current_question
    q_data = questions[q_idx]

    st.markdown(f"**Q{q_idx+1}:** {q_data['question']}")

    # Initialize selection for this question
    if f"answer_{q_idx}" not in st.session_state:
        st.session_state[f"answer_{q_idx}"] = None

    # Function to create large buttons using HTML
    def option_button(label, key):
        clicked = st.button(label, key=key)
        st.markdown(
            f"""
            <style>
            div[role="button"] {{
                width: 100%;
                height: 60px;
                font-size: 20px;
                margin: 5px 0;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
        return clicked

    # --- 2x2 grid ---
    row1_col1, row1_col2 = st.columns(2)
    row2_col1, row2_col2 = st.columns(2)
    cols = [row1_col1, row1_col2, row2_col1, row2_col2]

    for i, col in enumerate(cols):
        with col:
            if option_button(f"{q_data['options'][i]}", key=f"{q_idx}_{i}"):
                st.session_state[f"answer_{q_idx}"] = q_data['options'][i]

    # Show selected answer
    if st.session_state[f"answer_{q_idx}"]:
        st.success(f"✅ You selected: {st.session_state[f'answer_{q_idx}']}")

    # Navigation buttons
    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("⬅ Previous Question") and q_idx > 0:
            st.session_state.current_question -= 1
    with col_next:
        if st.button("Next Question ➡") and q_idx < len(questions) - 1:
            st.session_state.current_question += 1
