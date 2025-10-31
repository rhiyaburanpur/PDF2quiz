import re
import os
import json
import time 
import random # Needed for option shuffling and heuristic question generation
from PyPDF2 import PdfReader
from typing import List, Dict, Any
# FIX: Renaming the import alias to avoid collision with system files
import docx as docx_module 
from pptx import Presentation
from io import BytesIO

# --- Configuration Notes ---
# External LLM dependency has been removed to ensure zero-cost operation.
# Question generation is now performed using a Rule-Based Heuristic Approach.

# --- Multi-File Extraction Utility Functions (Unchanged) ---

def extract_text_from_pdf(uploaded_file, selected_pages):
    """Extracts text from selected PDF pages."""
    if not uploaded_file: return ""
    try:
        uploaded_file.seek(0)
        reader = PdfReader(uploaded_file)
        full_text = []
        page_indices = [p - 1 for p in selected_pages if 0 <= p - 1 < len(reader.pages)]
        for page_index in page_indices:
            page = reader.pages[page_index]
            text = page.extract_text()
            if text: full_text.append(text)
        return "\n".join(full_text)
    except Exception as e:
        print(f"Error during PDF text extraction: {e}")
        return ""

def extract_text_from_docx(uploaded_file):
    """Extracts text from a DOCX file."""
    if not uploaded_file: return ""
    try:
        uploaded_file.seek(0)
        # UPDATED: Use the imported alias docx_module
        document = docx_module.Document(BytesIO(uploaded_file.read()))
        full_text = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
        return "\n".join(full_text)
    except Exception as e:
        print(f"Error during DOCX text extraction: {e}")
        return ""

def extract_text_from_pptx(uploaded_file):
    """Extracts text from a PPTX file."""
    if not uploaded_file: return ""
    try:
        uploaded_file.seek(0)
        prs = Presentation(BytesIO(uploaded_file.read()))
        full_text = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    if shape.text.strip():
                        full_text.append(shape.text)
        return "\n".join(full_text)
    except Exception as e:
        print(f"Error during PPTX text extraction: {e}")
        return ""

def get_text_content(uploaded_file, selected_pages, file_type):
    """Selects the correct extraction method based on file_type."""
    if file_type == 'pdf':
        return extract_text_from_pdf(uploaded_file, selected_pages)
    elif file_type == 'docx':
        return extract_text_from_docx(uploaded_file)
    elif file_type == 'pptx':
        return extract_text_from_pptx(uploaded_file)
    else:
        return ""

def chunk_text(text, chunk_size=3000, overlap=500):
    """Splits the input text into manageable chunks for the heuristic generator."""
    if not text: return []
    # Basic sentence tokenization using regex split by periods, question marks, and exclamation marks
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', text)
    
    # Simple chunking based on sentence count (simpler for heuristic analysis)
    # Rejoining sentences up to the desired length
    current_chunk = ""
    chunks = []
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += " " + sentence
            
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks

# --- Heuristic Question Generation (Replacement for LLM API) ---

def generate_questions_heuristically(text_chunk: str, num_questions_per_chunk: int) -> List[Dict[str, Any]]:
    """
    Generates fill-in-the-blank questions based on simple keyword extraction.
    
    This function replaces the previous LLM API call.
    """
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', text_chunk)
    quiz_data = []
    
    # 1. Gather all potential keywords for distractors
    # Heuristic: Use capitalized words (likely proper nouns or acronyms) and numbers
    all_keywords = set()
    for sentence in sentences:
        # Find capitalized words (excluding start of sentence if not a noun)
        capitalized_words = re.findall(r'\b[A-Z][a-z]+\b', sentence)
        # Find numbers
        numbers = re.findall(r'\b\d{2,}\b', sentence)
        
        # Add to the pool, removing duplicates
        all_keywords.update(capitalized_words)
        all_keywords.update(numbers)
        
    keyword_list = list(all_keywords)

    # 2. Iterate and generate questions
    for sentence in sentences:
        if len(quiz_data) >= num_questions_per_chunk:
            break
            
        # Try to find a good answer candidate in the sentence
        candidate_matches = re.findall(r'\b([A-Z][a-z]+|\d{2,})\b', sentence)
        
        if not candidate_matches:
            continue
            
        # Pick a random candidate word from the sentence as the correct answer
        correct_answer = random.choice(candidate_matches)
        
        # Remove the correct answer from the sentence and replace with a blank
        # Use regex to replace only the first occurrence for clarity
        question_text = re.sub(r'\b' + re.escape(correct_answer) + r'\b', '_______', sentence, 1)
        
        # Ensure the question is meaningful and not just a fragment
        if '_______' not in question_text:
            continue
            
        # 3. Generate 3 Distractors
        # Distractors are picked from the general keyword list, excluding the correct answer
        distractor_pool = [k for k in keyword_list if k != correct_answer]
        
        # Ensure there are enough unique distractors
        num_distractors = 3
        if len(distractor_pool) < num_distractors:
            # Fallback: repeat words or use simple placeholders if necessary
            distractors = random.choices(distractor_pool, k=num_distractors)
            if not distractors:
                distractors = ["Option 1", "Option 2", "Option 3"] # Absolute fallback
        else:
            distractors = random.sample(distractor_pool, num_distractors)
        
        # 4. Assemble the question item
        options = [correct_answer] + distractors
        
        # Shuffle is handled later in post_process_quiz_data, but we ensure structure here
        quiz_data.append({
            "question": question_text.strip(),
            "options": options,
            "correct_answer": correct_answer,
            "source_snippet": sentence.strip()
        })

    return quiz_data

# --- Post-processing and Deduplication (Now uses 'random' module) ---

def post_process_quiz_data(quiz_data: List[Dict[str, Any]], target_count: int) -> List[Dict[str, Any]]:
    """
    Performs deduplication, cleaning, and shuffling of options.
    Uses the 'random' module.
    """
    
    # Set to store canonical, simplified question text to detect duplicates
    seen_questions = set()
    final_questions = []

    for item in quiz_data:
        question_text = item.get('question', '').strip()
        
        # 1. Cleaning: Basic normalization (lowercase, remove punctuation, strip whitespace)
        normalized_q = re.sub(r'[^\w\s]', '', question_text).lower()
        
        # 2. Deduplication Check
        if normalized_q in seen_questions:
            continue
        
        seen_questions.add(normalized_q)
        
        # 3. Shuffle Options (Crucial for good MCQ design)
        options = item.get('options', [])
        correct_answer = item.get('correct_answer')
        
        if options:
            # We already imported random globally
            if isinstance(correct_answer, str):
                
                # Perform the shuffle
                random.shuffle(options)
                
                # Update the item with shuffled options
                item['options'] = options
                
        # 4. Final collection
        final_questions.append(item)
        
        # Stop if we hit the user-requested count after deduplication
        if len(final_questions) >= target_count:
            break
            
    return final_questions

# --- Main Orchestration Function ---

def run_question_generation(uploaded_file, selected_pages, difficulty, num_questions, q_type, mcq_type, file_type):
    """
    Main orchestration function: extracts text, chunks it, and calls the heuristic generator.
    
    Note: 'difficulty', 'q_type', and 'mcq_type' are now ignored by the free heuristic generator
    but kept in the signature for compatibility with the frontend structure.
    """
    # 1. Extraction
    text_content = get_text_content(uploaded_file, selected_pages, file_type)
    
    if not text_content:
        return []

    # 2. Chunking
    # Chunking uses sentence-based logic for better heuristic question quality
    chunks = chunk_text(text_content, chunk_size=3000)
    
    total_chunks = len(chunks)
    # Request slightly more questions initially to compensate for potential deduplication
    total_questions_to_request = int(num_questions * 2) # Request 100% more, as heuristics are less reliable
    
    questions_per_chunk = total_questions_to_request // total_chunks
    remaining_questions = total_questions_to_request % total_chunks
    
    all_quiz_data = []

    # 3. Generation (Loop through chunks)
    for i, chunk in enumerate(chunks):
        target_q_count = questions_per_chunk + (1 if i < remaining_questions else 0)
        
        if target_q_count > 0:
            # Call the free heuristic generator
            quiz_data_chunk = generate_questions_heuristically(
                chunk, 
                target_q_count
            )
            all_quiz_data.extend(quiz_data_chunk)
            
            # Note: We continue iterating to maximize the pool for effective deduplication.
            
    # 4. Post-processing/Deduplication
    final_data = post_process_quiz_data(all_quiz_data, num_questions)
    
    return final_data
