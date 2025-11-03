import streamlit as st
from PyPDF2 import PdfReader # Keep for PDF page preview functionality
import quiz_generator 
import time 
import io 

st.set_page_config(page_title="PDF2Quiz", layout="wide", page_icon="🧠")

# --- INITIALIZATION ---
if "page" not in st.session_state:
    st.session_state.page = "home"

if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None

if "total_pages" not in st.session_state:
    st.session_state.total_pages = 0

if "selected_pages" not in st.session_state:
    st.session_state.selected_pages = []

if "current_question" not in st.session_state:
    st.session_state.current_question = 1

if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = []

if "score" not in st.session_state:
    st.session_state.score = 0

if "answers" not in st.session_state:
    st.session_state.answers = {} # Stores user's selected answer for each question index

if "feedback" not in st.session_state:
    st.session_state.feedback = ""

if "time_start" not in st.session_state:
    st.session_state.time_start = None

if "timer_running" not in st.session_state:
    st.session_state.timer_running = False

# --- UTILITY FUNCTIONS ---

@st.cache_data(show_spinner=False)
def get_pdf_page_count(uploaded_file):
    """Reads the uploaded PDF file to determine the total number of pages."""
    try:
        # Using io.BytesIO to read the uploaded file content in memory
        pdf_reader = PdfReader(io.BytesIO(uploaded_file.getvalue()))
        return len(pdf_reader.pages)
    except Exception as e:
        st.error(f"Error reading PDF pages: {e}")
        return 0

def get_timer_duration(option):
    """Converts timer option string to seconds."""
    if "5 Minutes" in option: return 300
    if "10 Minutes" in option: return 600
    return None

def reset_quiz():
    """Resets all session state variables related to the quiz."""
    st.session_state.page = "home"
    st.session_state.quiz_data = []
    st.session_state.current_question = 1
    st.session_state.score = 0
    st.session_state.answers = {}
    st.session_state.feedback = ""
    st.session_state.time_start = None
    st.session_state.timer_running = False

def calculate_final_score():
    """Calculates the final score based on stored answers."""
    correct_count = 0
    total_q = len(st.session_state.quiz_data)
    for i in range(total_q):
        correct_answer = st.session_state.quiz_data[i]['correct_answer']
        user_answer = st.session_state.answers.get(i)
        if user_answer == correct_answer:
            correct_count += 1
    st.session_state.score = correct_count
    return correct_count

# --- CORE FUNCTION TO HANDLE GENERATION ---
def generate_quiz():
    """
    Handles the file type check and calls the backend question generator.
    Called when the 'Generate Quiz' button is clicked.
    """
    if st.session_state.uploaded_file is None:
        st.error("Please upload a file before generating the quiz.")
        return

    # Determine file type based on extension (required by backend)
    file_name = st.session_state.uploaded_file.name
    if file_name.lower().endswith('.pdf'):
        file_type = 'pdf'
        # Crucial check: if it's a PDF, selected_pages must not be empty
        if not st.session_state.selected_pages:
            st.error("Please select at least one page from the PDF to generate questions.")
            return
    elif file_name.lower().endswith('.docx'):
        file_type = 'docx'
        st.session_state.selected_pages = [] # Pages not applicable for DOCX/PPTX
    elif file_name.lower().endswith('.pptx'):
        file_type = 'pptx'
        st.session_state.selected_pages = [] # Pages not applicable for DOCX/PPTX
    else:
        st.error("Unsupported file type.")
        return

    # Reset quiz state before generation
    st.session_state.quiz_data = []
    st.session_state.current_question = 1
    st.session_state.score = 0
    st.session_state.answers = {}
    st.session_state.feedback = ""
    st.session_state.time_start = None
    st.session_state.timer_running = False


    with st.spinner(f"Analyzing {file_name} and generating questions..."):
       
        quiz_data = quiz_generator.run_question_generation(
            uploaded_file=st.session_state.uploaded_file,
            selected_pages=st.session_state.selected_pages,
            # Config. parameters 
            difficulty=st.session_state.difficulty, 
            q_type=st.session_state.question_type, 
            mcq_type=st.session_state.mcq_type, 
            num_questions=st.session_state.num_questions,
            file_type=file_type 
        )

    if quiz_data:
        st.session_state.quiz_data = quiz_data
        st.session_state.page = "quiz" 
        # Timer for Practice Mode
        if st.session_state.mode == "Practice" and st.session_state.timer_option != "No Timer":
            st.session_state.time_start = time.time()
            st.session_state.timer_running = True
            # For the timer to update, we need to rerun the app periodically in the quiz page
    else:
        st.error("Could not generate questions. The document may be empty or failed to process.")

def handle_answer_selection(q_idx, selected_option):
    """Records the user's answer and provides feedback based on the mode."""
    st.session_state.answers[q_idx] = selected_option
    q_data = st.session_state.quiz_data[q_idx]
    
    is_correct = (selected_option == q_data['correct_answer'])
    
    if st.session_state.mode == "Learning":
        # Learning Mode: Immediate feedback
        if is_correct:
            st.session_state.feedback = "✅ Correct! Well done."
            st.session_state.score += 1 # Update score immediately
            st.balloons()
        else:
            st.session_state.feedback = f"❌ Incorrect. The correct answer is **{q_data['correct_answer']}**."
        
        # Show explanation/source snippet
        st.session_state.feedback += f"\n\n**Source Context:** {q_data['source_snippet']}"
    
    elif st.session_state.mode == "Practice":
        # Practice Mode: No immediate score update, just store the answer
        st.session_state.feedback = "Answer recorded. Click 'Next Question' to continue."

    # Rerun to update the feedback display
    st.rerun() # <-- FIX APPLIED HERE

def next_question():
    """Moves to the next question or the results page."""
    total_q = len(st.session_state.quiz_data)
    
    # Check if the current question has been answered (essential for Practice Mode logic)
    q_idx = st.session_state.current_question - 1
    if st.session_state.mode == "Practice" and q_idx not in st.session_state.answers:
        st.warning("Please select an answer before moving to the next question.")
        return

    st.session_state.feedback = "" # Clear feedback for the new question
    
    if st.session_state.current_question < total_q:
        st.session_state.current_question += 1
        st.rerun() # <-- FIX APPLIED HERE
    else:
        # End of quiz - calculate score and navigate to results
        calculate_final_score()
        st.session_state.page = "results"
        st.session_state.timer_running = False # Stop the timer
        st.rerun() # <-- FIX APPLIED HERE


# --- QUIZ PAGE IMPLEMENTATION ---

def quiz_page():
    # Timer Logic (runs only in Practice Mode)
    if st.session_state.timer_running and st.session_state.mode == "Practice" and st.session_state.timer_option != "No Timer":
        total_duration = get_timer_duration(st.session_state.timer_option)
        elapsed_time = time.time() - st.session_state.time_start
        remaining_time = max(0, total_duration - elapsed_time)
        
        # Check if time is up
        if remaining_time == 0:
            st.session_state.timer_running = False
            st.session_state.page = "results"
            calculate_final_score()
            st.warning("Time's up! Submitting your answers.")
            time.sleep(1) # Pause for user to see the message
            st.rerun() # <-- FIX APPLIED HERE
        
        # Display Timer
        minutes = int(remaining_time // 60)
        seconds = int(remaining_time % 60)
        
        if remaining_time < 60:
            timer_color = "red"
        else:
            timer_color = "green"

        st.markdown(
            f'<div style="background-color: #f0f2f6; padding: 10px; border-radius: 10px; text-align: center; color: {timer_color}; font-size: 24px; font-weight: bold;">'
            f'Time Remaining: {minutes:02d}:{seconds:02d}'
            '</div>', 
            unsafe_allow_html=True
        )
        # Force a rerun every second to update the timer display
        time.sleep(1)
        st.rerun() # <-- FIX APPLIED HERE


    # Header and Progress
    st.title(f"{st.session_state.mode} Mode Quiz")
    
    total_q = len(st.session_state.quiz_data)
    current_q_num = st.session_state.current_question
    q_idx = current_q_num - 1
    
    # Progress Bar
    progress_percent = (current_q_num - 1) / total_q
    st.progress(progress_percent, text=f"Question {current_q_num} of {total_q}")
    
    # Get current question data
    if not st.session_state.quiz_data:
        st.warning("No quiz data found. Please return to the Home page.")
        return

    q_data = st.session_state.quiz_data[q_idx]
    
    st.subheader(f"Q{current_q_num}: {q_data['question']}")
    
    # Display Options as Radio Buttons or Buttons
    # Using st.radio to ensure only one answer is selected and to simplify state management
    
    # --- Option Selection ---
    user_selection = st.radio(
        "Select your answer:",
        options=q_data['options'],
        index=None, # No default selection
        key=f"q_radio_{q_idx}"
    )

    # --- Handle Submission/Answer Recording ---
    # Only process if a selection is made and it hasn't been recorded yet
    if user_selection and st.session_state.answers.get(q_idx) is None:
        handle_answer_selection(q_idx, user_selection)
        
    # --- Display Feedback ---
    # Display recorded answer for Practice Mode, or feedback for Learning Mode
    if st.session_state.mode == "Practice" and st.session_state.answers.get(q_idx):
        st.info("Answer selected. Click Next to continue.")
    
    if st.session_state.mode == "Learning" and st.session_state.feedback:
        st.markdown(f"**Feedback:** {st.session_state.feedback}")


    # --- Navigation ---
    col_nav_1, col_nav_2, col_nav_3 = st.columns([1, 1, 4])

    with col_nav_1:
        if current_q_num > 1:
            if st.button("<< Previous"):
                st.session_state.current_question -= 1
                st.session_state.feedback = "" # Clear feedback
                st.rerun() # <-- FIX APPLIED HERE

    with col_nav_2:
        # Button label changes if it's the last question
        next_label = "Finish Quiz" if current_q_num == total_q else "Next Question >>"
        # Only allow navigation if an answer is selected OR if in Learning mode (where feedback is immediate)
        if st.session_state.answers.get(q_idx) or st.session_state.mode == "Learning":
            if st.button(next_label, type="primary"):
                next_question()
        elif st.session_state.mode == "Practice":
            st.button(next_label, disabled=True, help="Select an answer first.")
    
    # The third column is left empty for spacing


# --- RESULTS PAGE IMPLEMENTATION ---
def results_page():
    total_q = len(st.session_state.quiz_data)
    final_score = st.session_state.score
    percentage = (final_score / total_q) * 100 if total_q > 0 else 0
    
    st.title("🎉 Quiz Results")
    
    col_score, col_review = st.columns([1, 3])
    
    with col_score:
        st.markdown("### Final Score")
        st.metric(label="Total Correct", value=f"{final_score} / {total_q}")
        
        # Award badge based on percentage
        if percentage >= 90:
            st.balloons()
            badge = "🥇 Gold Star Performance"
        elif percentage >= 70:
            badge = "🥈 Silver Badge"
        elif percentage >= 50:
            badge = "🥉 Bronze Effort"
        else:
            badge = "Keep practicing!"
        
        st.info(badge)

        if st.button("Start New Quiz", on_click=reset_quiz, type="primary"):
             pass # Logic handled by reset_quiz


    with col_review:
        st.markdown("### Review Your Answers")
        
        # Review Mode: Show all questions, user answers, and correct answers
        for i, q_data in enumerate(st.session_state.quiz_data):
            user_answer = st.session_state.answers.get(i, "No Answer Selected")
            is_correct = (user_answer == q_data['correct_answer'])
            
            icon = "✅" if is_correct else "❌"
            
            st.markdown(f"#### {icon} Q{i+1}: {q_data['question']}")
            st.markdown(f"**Your Answer:** `{user_answer}`")
            st.markdown(f"**Correct Answer:** `{q_data['correct_answer']}`")
            st.markdown(f"**Source Context:** *{q_data['source_snippet']}*")
            st.markdown("---")


# --- Main Application Flow ---

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

# --- HOME PAGE (CONFIGURATION) ---
if st.session_state.page == "home":
    
    # Handle page count and selection only for PDFs
    if st.session_state.uploaded_file and st.session_state.uploaded_file.name.lower().endswith('.pdf'):
        # Get and cache the page count only when a new PDF is uploaded
        current_page_count = get_pdf_page_count(st.session_state.uploaded_file)
        st.session_state.total_pages = current_page_count
    
    # If the file is not a PDF, reset the page count and selection
    elif st.session_state.uploaded_file and not st.session_state.uploaded_file.name.lower().endswith('.pdf'):
        st.session_state.total_pages = 0
        st.session_state.selected_pages = []
    
    # Case where file is un-uploaded or session is fresh
    else:
        st.session_state.total_pages = 0
        st.session_state.selected_pages = []


    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("Quiz Configuration")

        # Configuration settings
        st.session_state.mode = st.selectbox("Select Mode", ["Learning", "Practice"], key="mode_q")
        st.session_state.num_questions = st.number_input("Number of Questions", min_value=1, max_value=50, value=10, key="num_q")
        st.session_state.difficulty = st.selectbox("Difficulty Level", ["Easy", "Medium", "Hard"], key="difficulty_q")
        st.session_state.question_type = st.selectbox("Question Type", ["Multiple Choice"], key="type_q")
        st.session_state.mcq_type = st.selectbox("MCQ Type", ["Single Answer"], key="mcq_type_q")
        st.session_state.timer_option = st.selectbox("Timer Option (Practice Mode)", ["No Timer", "5 Minutes", "10 Minutes"], key="timer_option_q")


        # ATTACHING THE CALL TO THE BUTTON
        st.button("🧠 Generate Quiz", on_click=generate_quiz, type="primary")

    with col2:
        st.title("Document-to-Quiz Generator")
        # File Uploader
        st.session_state.uploaded_file = st.file_uploader(
            "Upload Document (PDF, DOCX, PPTX)", 
            type=["pdf", "docx", "pptx"], 
            key="file_uploader_widget"
        )
        
        # --- PDF PAGE SELECTION LOGIC ---
        if st.session_state.uploaded_file and st.session_state.uploaded_file.name.lower().endswith('.pdf'):
            if st.session_state.total_pages > 0:
                all_pages = list(range(1, st.session_state.total_pages + 1))
                
                # Update selected_pages with the multiselect widget
                st.session_state.selected_pages = st.multiselect(
                    "Select Pages for Generation (PDF)",
                    options=all_pages,
                    default=all_pages, # Select all pages by default
                    key="page_selector"
                )
                st.caption(f"Total pages detected: {st.session_state.total_pages}")
            else:
                st.warning("Could not read page count from PDF.")
        # --- END PDF PAGE SELECTION LOGIC ---
        st.markdown("Upload your document (PDF, DOCX, PPTX) and instantly generate customized quizzes for learning or practice.")
        st.info("This generator uses a local Hugging Face AI Model to analyze your document's text and create high-quality, contextual Multiple-Choice Questions.")


# --- Page Routing ---
if st.session_state.page == "quiz":
    quiz_page()
elif st.session_state.page == "results":
    results_page()
# Home page is handled directly above
