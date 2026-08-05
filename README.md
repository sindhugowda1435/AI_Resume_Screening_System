# AI Resume Screener

A simple, self-contained resume screening tool. Paste a job description, upload
(or paste) resumes, and get a match score, a verdict, and matched/missing
skill breakdowns — all with a Python/Flask backend and a plain HTML/CSS/JS
frontend (no frameworks, no build step).

## How the "AI" scoring works

There's no external API call — everything runs locally and instantly:

1. **Text similarity** — TF-IDF vectorization + cosine similarity
   (scikit-learn) compares the overall language of the resume against the
   job description.
2. **Skill keyword overlap** — Both texts are scanned against a built-in
   vocabulary of ~50 common tech/business skills; the overlap becomes a
   percentage score.
3. **Final score** = `0.6 × text similarity + 0.4 × skill overlap`, mapped to
   a verdict: Strong / Moderate / Weak / Poor Match.
4. Basic contact info (email, phone, years of experience) is pulled out with
   regex for a quick glance.

You can tune the weighting or extend `COMMON_SKILLS` in `app.py` to fit your
own domain.

## Setup

```bash
# 1. Install dependencies
pip install flask scikit-learn pypdf

# 2. Run the app
python app.py

# 3. Open in your browser
http://127.0.0.1:5000
```

## Project structure

```
resume-screener/
├── app.py               # Flask backend: routes, extraction, scoring
├── templates/
│   └── index.html       # Page markup
├── static/
│   ├── style.css         # Styling (dossier / case-file theme)
│   └── script.js          # Tabs, drag-and-drop upload, API calls, rendering
├── uploads/              # Temp storage for uploaded files (auto-cleared)
└── README.md
```

## Features

- Paste a job description, then either:
  - **Upload multiple resumes** (PDF, DOCX, or TXT) via click or drag-and-drop, or
  - **Paste a single resume's text** directly.
- Batch screening — upload several resumes at once; results are ranked by
  score, highest first.
- Per-resume breakdown: overall score, text-match %, skill-match %, matched
  skills, missing skills, and extracted contact info.
- No database, no external AI API keys, nothing to configure.

## Notes / limitations

- Skill detection uses a fixed keyword list (`COMMON_SKILLS` in `app.py`) —
  add your own terms for better coverage in a specific field.
- DOCX parsing reads raw text only; complex formatting (tables, text boxes)
  may not be captured.
- This is a screening *aid*, not a hiring decision-maker — always have a
  human review shortlisted and rejected candidates.
- The Flask dev server (`app.run(debug=True)`) is for local use only; use a
  production WSGI server (e.g. gunicorn) if you deploy this.
