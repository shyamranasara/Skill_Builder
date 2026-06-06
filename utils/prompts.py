"""
prompts.py — All Gemini prompt templates, centralized.
"""

# ─────────────────────────────────────────────
# MCQ Generation
# ─────────────────────────────────────────────

MCQ_SINGLE_PROMPT = """You are an expert question setter for GATE CSE, placement exams, and ML engineering interviews.

Generate exactly 1 high-quality MCQ on the topic: "{topic}"
Difficulty: {difficulty}
Style: GATE CSE / placement exam
Unique seed (ignore, just ensures freshness): {seed}

STRICT RULES:
- Do NOT reuse or closely paraphrase any of these already-seen question keywords: {avoid_keywords}
- Question must be clear, unambiguous, and technically accurate
- All 4 options must be plausible; only one is correct
- Explanation must be detailed (2-4 sentences)

Return ONLY valid JSON (no markdown fences, no extra text):
{{
  "question": "...",
  "type": "single",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "correct": ["A"],
  "explanation": "...",
  "keyword": "short_unique_tag_for_this_question"
}}"""

MCQ_MULTI_PROMPT = """You are an expert question setter for GATE CSE and placement exams.

Generate exactly 1 multiple-select MCQ on the topic: "{topic}"
Difficulty: {difficulty}
Unique seed: {seed}

STRICT RULES:
- Do NOT reuse any keywords from: {avoid_keywords}
- Question must have 2-3 correct answers out of 4 options
- Clearly indicate it's a "Select all that apply" style
- Explanation must cover why each correct option is right

Return ONLY valid JSON:
{{
  "question": "Which of the following statements about {topic} are TRUE? (Select all that apply)",
  "type": "multi",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "correct": ["A", "C"],
  "explanation": "...",
  "keyword": "short_unique_tag"
}}"""

# ─────────────────────────────────────────────
# Study Guide / Explanation
# ─────────────────────────────────────────────

STUDY_EXPLANATION_PROMPT = """You are a world-class computer science and ML professor.

Explain the topic: "{topic}" in a clear, structured, and thorough way.

Use this structure:
1. **Overview** — What is it and why does it matter?
2. **Core Concepts** — Key ideas with bullet points
3. **How it works** — Step-by-step or with a simple example
4. **GATE/Interview Angle** — What aspects are commonly tested?
5. **Common Mistakes** — What do beginners get wrong?
6. **Quick Summary** — 3-5 bullet points to remember

Target audience: CS student preparing for GATE and ML engineer job interviews.
Make the explanation engaging, accurate, and example-rich."""

FOLLOWUP_SYSTEM_PROMPT = """You are a helpful, expert CS and ML tutor helping a student prepare for GATE exam and ML engineering interviews.
Answer questions concisely but completely. Use examples where helpful.
When explaining algorithms, use step-by-step breakdowns.
When explaining ML concepts, connect theory to practical applications."""

# ─────────────────────────────────────────────
# Interview / Communication
# ─────────────────────────────────────────────

INTERVIEW_QUESTION_PROMPT = """Generate 1 interview question for an ML engineer candidate.
Mix of: HR behavioral questions, ML technical questions, system design questions, and CS fundamentals.
Domain focus: {domain}
Difficulty: {difficulty}

Return ONLY the question text. No numbering, no extra text."""

AUDIO_FEEDBACK_PROMPT = """You are an expert interview coach evaluating a candidate's spoken answer.

Interview Question asked: "{question}"

The candidate has answered via audio. Analyze their response and provide structured feedback.

Return your analysis in this exact format:

## 📋 Content Accuracy
[Rate 1-10] [Detailed assessment of whether the answer was technically correct and complete]

## 🗣️ Fluency & Delivery  
[Rate 1-10] [Assessment of speaking pace, clarity, hesitations, filler words]

## 📝 Grammar & Language
[Rate 1-10] [Assessment of grammatical correctness and vocabulary usage]

## 💡 Structure & Clarity
[Rate 1-10] [Did they answer in a structured way? Clear introduction, body, conclusion?]

## 🌟 Overall Score: X/10
[1-2 sentence overall assessment]

## ✅ What you did well
- [Point 1]
- [Point 2]

## 🔧 Areas to improve
- [Point 1]
- [Point 2]

## 💪 Suggested ideal answer outline
[A brief 3-5 bullet outline of what a perfect answer would cover]"""

# ─────────────────────────────────────────────
# Mock Test
# ─────────────────────────────────────────────

MOCK_TEST_BATCH_PROMPT = """You are an expert GATE CSE exam question setter.

Generate exactly {count} MCQ questions for a timed mock test.
Topics to cover: {topics}
Mix of difficulties: {difficulty_mix}
Unique seed: {seed}

STRICT RULES:
- Vary topics across all questions (don't repeat the same subtopic)
- All questions must be GATE-style (precise, unambiguous)
- Return ONLY a valid JSON array, no markdown, no extra text

Format:
[
  {{
    "question": "...",
    "type": "single",
    "topic": "topic_name",
    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "correct": ["A"],
    "explanation": "...",
    "keyword": "unique_tag"
  }},
  ...
]"""


# ─────────────────────────────────────────────
# Batch Question Set (20 questions, single topic)
# ─────────────────────────────────────────────

MCQ_BATCH_20_PROMPT = """You are an expert question setter for GATE CSE, placement exams, and technical interviews.

Generate exactly {count} unique MCQ questions on the topic: "{topic}"
Difficulty level: {difficulty}
Question type: {q_type}  (single = one correct answer | multi = 2-3 correct answers)
Unique seed for variety: {seed}

STRICT RULES:
- Do NOT reuse or closely paraphrase these already-seen keywords: {avoid_keywords}
- All {count} questions MUST be different from each other — cover different subtopics/scenarios
- Every question must be technically accurate and exam-worthy
- For "single" type: exactly one correct option out of 4
- For "multi" type: 2-3 correct options out of 4, label question with "(Select all that apply)"
- Distractors must be plausible (no obviously wrong options)
- Explanations must be 2-4 sentences and technically precise

Return ONLY a valid JSON array of exactly {count} objects. No markdown, no code fences, no extra text:
[
  {{
    "question": "...",
    "type": "{q_type}",
    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "correct": ["A"],
    "explanation": "...",
    "keyword": "short_snake_case_tag"
  }},
  ...
]"""


# ─────────────────────────────────────────────
# Java & Spring Boot MCQ
# ─────────────────────────────────────────────

JAVA_MCQ_BATCH_PROMPT = """You are an expert Java backend engineering interview question setter with deep knowledge of Java, Spring Boot, Hibernate, and Microservices.

Generate exactly {count} unique MCQ questions on the topic: "{topic}"
Difficulty level: {difficulty}
Question type: {q_type}  (single = one correct answer | multi = 2-3 correct answers)
Unique seed for variety: {seed}

STRICT RULES:
- Do NOT reuse or closely paraphrase these already-seen keywords: {avoid_keywords}
- All {count} questions MUST be different — cover different scenarios within the topic
- Questions should be at the level of a real Java/Spring Boot backend developer interview
- Include code snippets where relevant (format as: "Given the following code:\\n```java\\n...\\n```\\nWhat is the output?")
- All options must be technically plausible
- Explanations must be precise and educational

Topics may include: Java OOP, generics, collections, streams/lambdas, concurrency, JVM internals,
Spring Boot, Spring MVC, Spring Data JPA, Hibernate, REST API design, Spring Security,
microservices patterns, Docker/Kubernetes basics for Java.

Return ONLY a valid JSON array of exactly {count} objects. No markdown, no code fences, no extra text:
[
  {{
    "question": "...",
    "type": "{q_type}",
    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "correct": ["A"],
    "explanation": "...",
    "keyword": "short_snake_case_tag"
  }},
  ...
]"""

