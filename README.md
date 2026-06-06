# 🎓 GATE & ML Job Prep

A personal AI-powered study app for GATE CS exam preparation and ML Engineering job interviews.

**Tech Stack:** Python · Streamlit · Gemini 1.5 Flash · Plotly · $0/month

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Add your Gemini API key
Open `.env` and paste your key:
```
GEMINI_API_KEY=your_actual_key_here
```
Get a free key at: https://aistudio.google.com/app/apikey

### 3. Run the app
```bash
streamlit run app.py
```

App opens at: http://localhost:8501

---

## 📁 Project Structure

```
MCQ_Generated_Website/
├── app.py                        ← Dashboard (entry point)
├── pages/
│   ├── syllabus_tracker.py       ← GATE CS 2024 syllabus tracker
│   ├── cs_mcq.py                 ← DSA, OS, DBMS, CN MCQs
│   ├── aptitude_mcq.py           ← Quantitative & Reasoning MCQs
│   ├── english_mcq.py            ← Grammar & Vocabulary MCQs
│   ├── ml_mcq.py                 ← ML Engineering MCQs
│   ├── mock_test.py              ← Timed 30Q mock test
│   ├── study_guide.py            ← AI explanation + chat
│   └── communication.py          ← Voice interview practice
├── utils/
│   ├── gemini_service.py         ← All Gemini API calls
│   ├── firebase_service.py       ← Local session state (Firebase-ready)
│   ├── question_hash.py          ← Non-repeatable question engine
│   ├── prompts.py                ← All prompt templates
│   └── mcq_helper.py             ← JSON parsing + Streamlit rendering
├── data/
│   ├── gate_syllabus.json        ← Full GATE CS 2024 syllabus
│   └── ml_topics.json            ← ML engineering topics
├── .streamlit/
│   ├── config.toml               ← Dark theme + layout
│   └── secrets.toml              ← Local secrets (gitignored)
├── .env                          ← API keys (gitignored)
├── requirements.txt
└── README.md
```

---

## 🌟 Features

| Feature | Description |
|---------|-------------|
| 📚 Syllabus Tracker | Full GATE CS 2024 syllabus with checkbox tracking and progress bars |
| 💻 CS Core MCQs | DSA, OS, DBMS, Computer Networks — GATE style |
| 🧮 Aptitude MCQs | Quantitative, Reasoning, DI — GATE GA style |
| 📝 English MCQs | Grammar, Vocabulary, Comprehension |
| 🤖 ML MCQs | Transformers, MLOps, Feature Engineering, Evaluation |
| 🎯 Mock Test | Timed 30Q test with topic-wise breakdown chart |
| 📖 Study Guide | AI explanation + multi-turn chat Q&A |
| 🎤 Communication | Voice interview practice with AI feedback |

---

## 🔑 Getting a Gemini API Key (Free)

1. Go to https://aistudio.google.com/app/apikey
2. Click **Create API Key**
3. Copy the key
4. Paste into `.env`: `GEMINI_API_KEY=your_key`

The free tier gives you **1500 requests/day** — more than enough for daily prep.

---

## ☁️ Deploying to Streamlit Cloud (Free)

1. Push this project to a GitHub repo
2. Go to https://share.streamlit.io
3. Click **New app** → select your repo → set `app.py` as main file
4. In **Secrets**, add:
   ```
   GEMINI_API_KEY = "your_key"
   ```
5. Click **Deploy** → live in ~60 seconds

---

## 📌 Adding Firebase (Later)

When you're ready to persist data across sessions:

1. Create a Firebase project at https://console.firebase.google.com
2. Enable Firestore Database (Spark tier = free)
3. Download `serviceAccountKey.json`
4. Add `firebase-admin` to `requirements.txt`
5. Replace `utils/firebase_service.py` with the Firebase implementation
   (all function signatures stay the same — just swap the backing store)

---

## 🛠️ Notes

- **Non-repeatable MCQs**: A UUID seed + keyword hash engine prevents duplicate questions
- **Audio**: Voice recording requires Chrome/Edge browser. Falls back to text input if package missing
- **API Rate Limits**: Built-in exponential backoff retry logic handles Gemini rate limits
