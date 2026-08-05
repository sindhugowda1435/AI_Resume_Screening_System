"""
AI Resume Screening System
---------------------------
A simple Flask backend that scores resumes against a job description
using TF-IDF + cosine similarity (scikit-learn), plus keyword/skill
matching and basic contact-info extraction.

Run:
    python app.py
Then open http://127.0.0.1:5000 in your browser.
"""

import os
import re
import uuid

from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from pypdf  import PdfReader, pdfReader

# --------------------------------------------------------------------------
# App config
# --------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"pdf", "txt", "docx"}
MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB per file

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# A small built-in skills vocabulary used for keyword-overlap scoring.
# Feel free to extend this list for your own domain.
COMMON_SKILLS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "sql", "nosql",
    "html", "css", "react", "angular", "vue", "node.js", "node", "express",
    "flask", "django", "fastapi", "spring", "aws", "azure", "gcp",
    "docker", "kubernetes", "git", "linux", "machine learning", "deep learning",
    "nlp", "data analysis", "data science", "pandas", "numpy", "scikit-learn",
    "tensorflow", "pytorch", "excel", "tableau", "power bi", "communication",
    "leadership", "project management", "agile", "scrum", "rest api",
    "graphql", "ci/cd", "testing", "unit testing", "figma", "ui/ux",
    "product management", "sales", "marketing", "seo", "content writing",
    "customer service", "accounting", "finance", "hr", "recruiting",
]

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+?\d{1,3}[\s.-]?)?(\(?\d{3,4}\)?[\s.-]?)\d{3,4}[\s.-]?\d{3,4}")
YEARS_EXP_RE = re.compile(r"(\d+)\+?\s*(?:years|yrs)\s*(?:of)?\s*experience", re.IGNORECASE)


# --------------------------------------------------------------------------
# File text extraction
# --------------------------------------------------------------------------

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_pdf(path: str) -> str:
    text_parts = []
    with open(path, "rb") as f:
        reader = PdfReader(f)
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def extract_text_from_docx(path: str) -> str:
    # Minimal docx text extraction using the zip/xml structure,
    # avoiding an extra heavy dependency.
    import zipfile
    from xml.etree import ElementTree

    text_parts = []
    with zipfile.ZipFile(path) as z:
        with z.open("word/document.xml") as f:
            tree = ElementTree.parse(f)
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            for node in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"):
                text_parts.append(node.text or "")
    return " ".join(text_parts)


def extract_text_from_file(path: str, filename: str) -> str:
    ext = filename.rsplit(".", 1)[1].lower()
    if ext == "pdf":
        return extract_text_from_pdf(path)
    if ext == "docx":
        return extract_text_from_docx(path)
    if ext == "txt":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    return ""


# --------------------------------------------------------------------------
# Scoring logic
# --------------------------------------------------------------------------

def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s.+#/-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tfidf_similarity(resume_text: str, job_text: str) -> float:
    """Cosine similarity between resume and job description using TF-IDF."""
    corpus = [clean_text(resume_text), clean_text(job_text)]
    if not corpus[0] or not corpus[1]:
        return 0.0
    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        tfidf_matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        return 0.0
    sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    return round(float(sim) * 100, 2)


def extract_skills(text: str, vocabulary=COMMON_SKILLS):
    text_lower = text.lower()
    found = set()
    for skill in vocabulary:
        pattern = r"(?<![a-z0-9])" + re.escape(skill.lower()) + r"(?![a-z0-9])"
        if re.search(pattern, text_lower):
            found.add(skill)
    return sorted(found)


def keyword_overlap_score(resume_skills, job_skills):
    if not job_skills:
        return 0.0
    overlap = set(resume_skills) & set(job_skills)
    return round(len(overlap) / len(job_skills) * 100, 2)


def extract_contact_info(text: str):
    email_match = EMAIL_RE.search(text)
    phone_match = PHONE_RE.search(text)
    years_match = YEARS_EXP_RE.search(text)
    return {
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0).strip() if phone_match else None,
        "years_experience": years_match.group(1) if years_match else None,
    }


def score_resume(resume_text: str, job_text: str):
    resume_skills = extract_skills(resume_text)
    job_skills = extract_skills(job_text)

    similarity = tfidf_similarity(resume_text, job_text)
    keyword_score = keyword_overlap_score(resume_skills, job_skills)

    # Weighted final score: semantic similarity + skill keyword overlap
    final_score = round(similarity * 0.6 + keyword_score * 0.4, 2)

    matched_skills = sorted(set(resume_skills) & set(job_skills))
    missing_skills = sorted(set(job_skills) - set(resume_skills))

    contact = extract_contact_info(resume_text)

    if final_score >= 75:
        verdict = "Strong Match"
    elif final_score >= 50:
        verdict = "Moderate Match"
    elif final_score >= 25:
        verdict = "Weak Match"
    else:
        verdict = "Poor Match"

    return {
        "similarity_score": similarity,
        "keyword_score": keyword_score,
        "final_score": final_score,
        "verdict": verdict,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "resume_skills": resume_skills,
        "job_skills": job_skills,
        "contact": contact,
    }


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/screen", methods=["POST"])
def screen_resume():
    job_text = request.form.get("job_description", "").strip()
    if not job_text:
        return jsonify({"error": "Job description is required."}), 400

    resume_text = request.form.get("resume_text", "").strip()

    # Handle multiple uploaded resume files (batch screening)
    results = []

    uploaded_files = request.files.getlist("resume_files")
    uploaded_files = [f for f in uploaded_files if f and f.filename]

    if uploaded_files:
        for file in uploaded_files:
            if not allowed_file(file.filename):
                results.append({
                    "filename": file.filename,
                    "error": "Unsupported file type. Use PDF, DOCX, or TXT.",
                })
                continue

            filename = secure_filename(file.filename)
            unique_name = f"{uuid.uuid4().hex}_{filename}"
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            file.save(save_path)

            try:
                text = extract_text_from_file(save_path, filename)
                if not text.strip():
                    results.append({
                        "filename": filename,
                        "error": "Could not extract any text from this file.",
                    })
                    continue
                result = score_resume(text, job_text)
                result["filename"] = filename
                results.append(result)
            except Exception as exc:  # noqa: BLE001
                results.append({"filename": filename, "error": str(exc)})
            finally:
                if os.path.exists(save_path):
                    os.remove(save_path)

    elif resume_text:
        result = score_resume(resume_text, job_text)
        result["filename"] = "Pasted Resume"
        results.append(result)
    else:
        return jsonify({"error": "Provide resume text or upload at least one file."}), 400

    # Rank by final_score descending (errors sink to the bottom)
    results.sort(key=lambda r: r.get("final_score", -1), reverse=True)
    return jsonify({"results": results})
if __name__ == "__main__":
    app.run(debug=True)