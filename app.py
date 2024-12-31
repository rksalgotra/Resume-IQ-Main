from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
import pandas as pd
from resume_processor import extract_text_from_pdf, check_ats_compliance, calculate_experience, load_ats_rules, match_keywords, keywords_found

# Create Flask app instance
app = Flask(__name__)

# Configure upload folder and allowed extensions
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'txt'}

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load ATS compliance rules
ats_rules = load_ats_rules()

# Function to check if the file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    """Render the index page."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads and process resumes."""
    if 'resumes' not in request.files:
        return jsonify({"error": "No files part in the request"})

    resumes = request.files.getlist('resumes')
    experience_required = request.form.get('experience_required')
    job_description = request.form.get('job_description')

    # Validate form inputs
    if not resumes:
        return jsonify({"error": "No resumes uploaded"})
    if not experience_required or not job_description:
        return jsonify({"error": "Missing required fields"})

    try:
        experience_required = float(experience_required)
    except ValueError:
        return jsonify({"error": "Experience required must be a valid number"})

    # Parse the job description for keywords
    job_description_keywords = [keyword.strip() for keyword in job_description.split(',')]

    # Convert the list to a plain comma-separated string
    job_keywords = ', '.join(job_description_keywords)

    results = []
    for resume in resumes:
        if resume and allowed_file(resume.filename):
            filename = secure_filename(resume.filename)
            resume_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            resume.save(resume_path)

            try:
                # Extract text and evaluate ATS compliance
                resume_text = extract_text_from_pdf(resume_path)
                ats_compliant = check_ats_compliance(resume_text, ats_rules)
                experience = calculate_experience(resume_text, job_description_keywords)
                
                # Extract Matching Skills Score
                matching_skills_score = match_keywords(resume_text, job_description_keywords)

                # Extract Matching Skills
                matching_skills = keywords_found(resume_text, job_description_keywords)    
                matched_keywords = ', '.join(matching_skills)            

                # Calculate scores and evaluate the candidate
                total_experience = sum(experience.values())
                required_experience = experience_required * 12  # Convert years to months
                score = (total_experience / required_experience) * 100 if required_experience > 0 else 0

                # Remove the extension and get only the base name
                file_name_without_extension = os.path.splitext(filename)[0]

                result = {
                    'Profile Name': file_name_without_extension,
                    'Skills Required':job_keywords,
                    'Skills Matched':matched_keywords,
                    'Skill Match': f"{matching_skills_score:.2f}%",
                    'ATS Compliance': f"{ats_compliant:.2f}%",
                    #'Experience Match Score': f"{score:.2f}%",
                    'Relevant Experience in Months': experience,
                    'Result': "Shortlisted" if matching_skills_score >= 70 and ats_compliant >= 75 else "Not Shortlisted"
                }
                results.append(result)
            except Exception as e:
                results.append({
                    'Profile Name': filename,
                    'Skills Required':'Error',
                    'Skills Matched':'Error',                    
                    'Skill Match': 'Error processing resume',
                    'ATS Compliance': 'Error',
                    #'Experience Match Score': 'Error',
                    'Relevant Experience in Months': 'Error',
                    'Result': 'Error',
                    'Error': str(e)
                })

    # Display results in a table format
    df = pd.DataFrame(results)
    return render_template('index.html', results=df.to_html(classes='table table-striped'))

if __name__ == '__main__':
    app.run(debug=True)
