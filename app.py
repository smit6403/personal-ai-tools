import os
import sys
import math
import json
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

_api_key = os.environ.get("OPENAI_API_KEY", "")
client = OpenAI(api_key=_api_key) if _api_key else None

def _check_client():
    if not client:
        return None, jsonify({"status": "error", "message": "OPENAI_API_KEY is not set. Go to Render → Environment Variables and add it."})
    return client, None

rag_store = {"chunks": [], "embeddings": [], "doc_names": [], "loaded_docs": []}

def _extract_pdf_text(file_storage):
    reader = PdfReader(file_storage)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)

def _chunk_text(text, chunk_size=600, overlap=120):
    chunks, start = [], 0
    while start < len(text):
        chunk = text[start:start + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

def _embed(texts):
    response = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [item.embedding for item in response.data]

def _cosine_similarity(a, b):
    dot   = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    return dot / (mag_a * mag_b + 1e-10)

def _retrieve_context(query, top_k=6):
    if not rag_store["chunks"]:
        return None
    query_vec = _embed([query])[0]
    scores = [_cosine_similarity(query_vec, emb) for emb in rag_store["embeddings"]]
    top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    relevant = [i for i in top_idx if scores[i] > 0.25]
    if not relevant:
        relevant = top_idx[:3]
    return "\n\n---\n\n".join(rag_store["chunks"][i] for i in relevant)

TONE_PROFILES = {
    "analytical": """You are Nexus Core, an elite analytical intelligence.

Your standards:
- Lead with the most important insight, not preamble
- Use precise language; avoid vague qualifiers like "quite" or "somewhat"
- Structure complex answers with clear headers and numbered steps
- Cite reasoning explicitly — show your work
- When uncertain, say so and give confidence levels
- End with actionable implications when relevant""",

    "creative": """You are Nexus Core, a brilliantly creative intelligence.

Your standards:
- Open with an unexpected angle or analogy that reframes the topic
- Use concrete, vivid examples — not generic ones
- Connect ideas across disciplines when it illuminates the point
- Balance creativity with accuracy — never sacrifice correctness for flair
- Make abstract concepts feel tangible and real""",

    "technical": """You are Nexus Core, a world-class senior engineer and technical expert.

Your standards:
- Provide complete, production-ready code — never pseudocode unless explicitly asked
- Always include error handling, edge cases, and type hints
- Explain *why* not just *what* — architectural decisions matter
- Point out common pitfalls and how to avoid them
- If there are multiple approaches, briefly compare them and recommend one
- Test your logic mentally before writing it""",

    "tutor": """You are Nexus Core, an exceptional educator who has taught at the world's best universities.

Your standards:
- First diagnose what the student actually needs — don't assume
- Build from first principles; never skip foundational steps
- Use the Socratic method when appropriate — guide discovery
- Give a concrete worked example for every abstract concept
- Check for understanding by posing a follow-up micro-question at the end
- Adjust complexity based on the student's apparent level
- Make it memorable: use mnemonics, analogies, or visual descriptions""",
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_document():
    ai_client, err = _check_client()
    if err: return err
    uploaded_file = request.files.get("file")
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"status": "error", "message": "No file provided."})
    if not uploaded_file.filename.lower().endswith(".pdf"):
        return jsonify({"status": "error", "message": "Only PDF files are supported."})
    filename = uploaded_file.filename
    try:
        text = _extract_pdf_text(uploaded_file)
        if not text.strip():
            return jsonify({"status": "error", "message": "No text extracted — PDF may be image-based."})
        chunks = _chunk_text(text)
        all_embeddings = []
        for i in range(0, len(chunks), 100):
            all_embeddings.extend(_embed(chunks[i:i+100]))
        rag_store["chunks"].extend(chunks)
        rag_store["embeddings"].extend(all_embeddings)
        rag_store["doc_names"].extend([filename] * len(chunks))
        if filename not in rag_store["loaded_docs"]:
            rag_store["loaded_docs"].append(filename)
        return jsonify({"status": "success", "message": f"Loaded {len(chunks)} chunks from '{filename}'.",
                        "loaded_docs": rag_store["loaded_docs"], "total_chunks": len(rag_store["chunks"])})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)})

@app.route("/knowledge-base", methods=["GET"])
def knowledge_base_status():
    return jsonify({"loaded_docs": rag_store["loaded_docs"], "total_chunks": len(rag_store["chunks"])})

@app.route("/knowledge-base/clear", methods=["POST"])
def clear_knowledge_base():
    for key in ("chunks", "embeddings", "doc_names", "loaded_docs"):
        rag_store[key].clear()
    return jsonify({"status": "success", "message": "Knowledge base cleared."})

@app.route("/process", methods=["POST"])
def process_directive():
    ai_client, err = _check_client()
    if err: return err
    prompt_text = (request.form.get("prompt", "") or "").strip()
    tone_key    = request.form.get("tone", "analytical")
    history_raw = request.form.get("history", "[]")
    try:
        temperature = max(0.0, min(2.0, float(request.form.get("temperature", 0.7))))
    except ValueError:
        temperature = 0.7
    try:
        top_p = max(0.0, min(1.0, float(request.form.get("top_p", 0.9))))
    except ValueError:
        top_p = 0.9
    try:
        history = json.loads(history_raw)
    except Exception:
        history = []

    system_prompt = TONE_PROFILES.get(tone_key, TONE_PROFILES["analytical"])
    document_text = ""
    uploaded_file = request.files.get("file")
    if uploaded_file and uploaded_file.filename:
        try:
            document_text = _extract_pdf_text(uploaded_file)
        except Exception as exc:
            return jsonify({"status": "error", "message": f"PDF extraction failed: {exc}"})

    if not prompt_text and not document_text:
        return jsonify({"status": "error", "message": "Please enter a prompt or upload a PDF."})

    rag_context = None
    if prompt_text and rag_store["chunks"]:
        try:
            rag_context = _retrieve_context(prompt_text)
        except Exception:
            pass

    parts = []
    if rag_context:
        parts.append("KNOWLEDGE BASE EXCERPTS:\n━━━━━━━━━━━━━━━━━━━━━━━\n" + rag_context +
                     "\n━━━━━━━━━━━━━━━━━━━━━━━\nUse these as your PRIMARY source. If the answer isn't in them, say so then answer from general knowledge.")
    if document_text:
        parts.append(f"[UPLOADED DOCUMENT]\n{document_text}\n[END DOCUMENT]")
    if prompt_text:
        parts.append(prompt_text)
    else:
        parts.append("Give me a comprehensive, well-structured analysis of the document above.")

    messages = [{"role": "system", "content": system_prompt}]
    for turn in history[-10:]:
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": "\n\n".join(parts)})

    try:
        response = ai_client.chat.completions.create(
            model="gpt-4o", messages=messages,
            temperature=temperature, top_p=top_p, max_tokens=8192)
        answer = response.choices[0].message.content
        return jsonify({"status": "success", "response": answer, "rag_active": rag_context is not None})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)})

@app.route("/study", methods=["POST"])
def study_mode():
    ai_client, err = _check_client()
    if err: return err
    data       = request.get_json(silent=True) or {}
    mode       = data.get("mode", "explain")
    subject    = data.get("subject", "")
    content    = data.get("content", "")
    question   = data.get("question", "")
    difficulty = data.get("difficulty", "intermediate")
    history    = data.get("history", [])

    MODE_INSTRUCTIONS = {
        "explain": "MODE: Deep Explanation\nDeliver a masterclass-level explanation. Structure: (1) Core concept in one sentence, (2) Why it matters, (3) Step-by-step breakdown from first principles, (4) Worked example, (5) Common mistakes, (6) One micro-question to check understanding.",
        "quiz": "MODE: Quiz Generation\nGenerate exactly 5 multiple-choice questions. For each:\nQ[n]: <question>\nA) <wrong>  B) <wrong>  C) <correct>  D) <wrong>\nAnswer: <letter>\nExplanation: <why correct AND why others are wrong>",
        "flashcards": "MODE: Flashcard Generation\nGenerate exactly 10 flashcard pairs:\nFRONT: <term, formula, or question>\nBACK: <clear, complete answer with units/context>\n---",
        "summarize": "MODE: Study Summary\nProduce a complete study sheet:\n## Core Concepts\n## Key Formulas / Facts\n## Relationships & Connections\n## Common Mistakes\n## Practice Questions (3 with full solutions)\n## 30-Second Review",
        "exam_prep": "MODE: Exam Coaching\nDeliver:\n## Highest-Priority Topics (ranked)\n## Topic Breakdown\n## Rapid-Fire Drill (10 short-answer Q&A)\n## Exam Strategy\n## Last-Minute Checklist",
    }

    system_prompt = (TONE_PROFILES["tutor"] + "\n\n" + MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS["explain"]) +
                     f"\n\nDifficulty: {difficulty.upper()}.")

    rag_context = None
    rag_query = subject or question or (content[:300] if content else "")
    if rag_query and rag_store["chunks"]:
        try:
            rag_context = _retrieve_context(rag_query)
        except Exception:
            pass

    parts = []
    if rag_context:
        parts.append("KNOWLEDGE BASE EXCERPTS:\n" + rag_context + "\nGround your response in these materials.")
    if subject:  parts.append(f"Topic: {subject}")
    if content:  parts.append(f"Material:\n{content}")
    if question: parts.append(f"Question: {question}")
    if not parts:
        return jsonify({"status": "error", "message": "Provide a subject, content, or question."})

    messages = [{"role": "system", "content": system_prompt}]
    for turn in history[-8:]:
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": "\n\n".join(parts)})

    try:
        response = ai_client.chat.completions.create(
            model="gpt-4o", messages=messages,
            temperature=0.4, top_p=0.9, max_tokens=8192)
        answer = response.choices[0].message.content
        return jsonify({"status": "success", "response": answer, "rag_active": rag_context is not None})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
