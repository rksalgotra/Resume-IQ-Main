import re
from datetime import datetime
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
import json
import os

# Load ATS rules
def load_ats_rules():
    with open("ats_rules.json", "r") as f:
        return json.load(f)

# Load OCR Model
model = ocr_predictor(pretrained=True)

# Extract text from PDF
def extract_text_from_pdf(pdf_path):
    doc = DocumentFile.from_pdf(pdf_path)
    result = model(doc)
    
    all_text = []
    for page in result.pages:
        for block in page.blocks:
            for line in block.lines:
                all_text.append(" ".join(word.value for word in line.words))
    return " ".join(all_text)

def extract_dates(text):
    date_patterns = [
        r"\b\d{1,2}/\d{1,2}/\d{4}\b",  # DD/MM/YYYY
        r"\b\d{4}-\d{2}-\d{2}\b",      # YYYY-MM-DD
        r"\b\d{4}/\d{2}\b",            # YYYY/MM
        r"\b[A-Za-z]{3}\s?\d{4}\b"     # Month YYYY
    ]
    dates = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                dates.append(parse_date(match))
            except ValueError:
                continue
    return dates

def parse_date(date_str):
    date_formats = [
        "%d/%m/%Y",  # DD/MM/YYYY
        "%Y-%m-%d",  # YYYY-MM-DD
        "%Y/%m",     # YYYY/MM
        "%b %Y"      # Month Year
    ]
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unknown date format: {date_str}")


# Match keywords and return Match Score
def match_keywords(text, keywords):
    matched = [keyword for keyword in keywords if keyword.lower() in text.lower()]
    match_count = len(matched)
    total_keywords = len(keywords)
    skill_match_score = (match_count / total_keywords) * 100 if total_keywords > 0 else 0
    return skill_match_score

# Match keywords and return only matching keywords
def keywords_found(text, keywords):
    matched = []
    for keyword in keywords:
        if keyword.lower() in text.lower():
            matched.append(keyword)
    return matched
"""
# Calculate experience in months based on extracted dates and keywords
def calculate_experience(employment_text, keywords):
    experience = {keyword: 0 for keyword in keywords}
    dates = extract_dates(employment_text)
    
    if len(dates) >= 2:
        for i in range(0, len(dates) - 1, 2):
            start, end = dates[i], dates[i + 1]
            
            # Ensure start date is before end date
            if start > end:
                start, end = end, start  # Swap dates if they're in the wrong order

            # Calculate duration in months
            duration_months = (end.year - start.year) * 12 + end.month - start.month
            if duration_months < 0:
                duration_months = 0  # Ensure that duration cannot be negative
            
            # Add experience for each keyword
            for keyword in keywords:
                if keyword in employment_text.lower():
                    experience[keyword] += duration_months
    
    return experience
"""
# Search for section headings and extract the relevant employment/project text
def extract_relevant_sections(text):
    # Define possible section headings
    section_headings = [
        "PROJECTS HANDLED", "Work History", "PROJECTS", "Employment History", 
        "Key Projects", "Work Experience", "PROJECT EXPERIENCE"
    ]
    
    relevant_text = ""
    
    # Check for section headings and extract the content following them
    for heading in section_headings:
        match = re.search(rf"({heading})(.*?)(?=\n[A-Z ]+|\Z)", text, re.IGNORECASE | re.DOTALL)
        if match:
            relevant_text += match.group(2)  # Append the content after the heading
    
    return relevant_text

# Calculate experience in months based on extracted dates and keywords
def calculate_experience(employment_text, keywords):
    experience = {keyword: 0 for keyword in keywords}
    
    # Extract the relevant sections of the resume
    relevant_text = extract_relevant_sections(employment_text)
    
    # Extract dates from the relevant sections
    dates = extract_dates(relevant_text)
    
    # If there are at least two dates (start and end dates), proceed with the calculations
    if len(dates) >= 2:
        for i in range(0, len(dates) - 1, 2):
            start, end = dates[i], dates[i + 1]
            
            # Ensure start date is before end date
            if start > end:
                start, end = end, start  # Swap dates if they're in the wrong order

            # Calculate duration in months
            duration_months = (end.year - start.year) * 12 + end.month - start.month
            if duration_months < 0:
                duration_months = 0  # Ensure that duration cannot be negative
            
            # Add experience for each keyword
            for keyword in keywords:
                if keyword in employment_text.lower():
                    experience[keyword] += duration_months
    
    return experience


# Check ATS compliance
def check_ats_compliance(text, ats_rules):
    """
    Evaluate the resume text against ATS compliance rules.
    
    Args:
        text (str): Extracted text from the resume.
        ats_rules (dict): Dictionary containing ATS compliance rules.
    
    Returns:
        float: ATS compliance score as a percentage.
    """
    score = 0
    total_criteria = 0

    # Check for mandatory labels (e.g., name, email, phone, LinkedIn)
    required_labels = ats_rules.get("required_labels", [])
    for label in required_labels:
        total_criteria += 1
        if label.lower() in text.lower():
            score += 1

    # Check for mandatory sections
    mandatory_sections = ats_rules.get("mandatory_sections", [])
    for section in mandatory_sections:
        total_criteria += 1
        if section.lower() in text.lower():
            score += 1

    # Check for accepted date formats
    date_pattern = ats_rules.get("date_pattern", r"\b(0[1-9]|1[0-2])\s?\d{4}\b")  # Default MM YYYY
    if re.search(date_pattern, text):
        total_criteria += 1
        score += 1

    # Calculate ATS compliance score as a percentage
    ats_score = (score / total_criteria) * 100 if total_criteria > 0 else 0
    return ats_score
