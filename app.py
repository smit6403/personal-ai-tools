import os
import sys
import math
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB

# ── OpenAI client ──────────────────────────────────────────────────────────
_api_key = os.environ.get("OPENAI_API_KEY", "")
client = OpenAI(api_key=_api_key) if _api_key else None


def _check_client():
    if not client:
        return None, jsonify({
            "status": "error",
            "message": "OPENAI_API_KEY is missing. Add it to Render → Environment Variables."
        })
    return client, None


# ── In-memory RAG store ────────────────────────────────────────────────────
rag_store = {
    "chunks":      [],   # list[str]
    "embeddings":  [],   # list[list[float]]
    "doc_names":   [],   # list[str] — filename for each chunk
    "loaded_docs": [],   # list[str] — unique filenames
}


def _extract_pdf_text(file_storage):
    reader = PdfReader(file_storage)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def _chunk_text(text, chunk_size=800, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + chunk_size])
        start += chunk_size - overlap
    return [c for c in chunks if c.strip()]


def _embed(texts):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    return [item.embedding for item in response.data]


def _cosine_similarity(a, b):
    dot   = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    return dot / (mag_a * mag_b + 1e-10)


def _retrieve_context(query, top_k=5):
    if not rag_store["chunks"]:
        return None
    query_vec = _embed([query])[0]
    scores = [_cosine_similarity(query_vec, emb) for emb in rag_store["embeddings"]]
    top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    return "\n\n---\n\n".join(rag_store["chunks"][i] for i in top_idx)


# ── Tone profiles ──────────────────────────────────────────────────────────
TONE_PROFILES = {
    "analytical": (
        "You are Nexus Core, an elite analytical reasoning engine. "
        "Be precise, evidence-driven, and thorough. Structure your answers "
        "with clear headings, bullet points where appropriate, and never "
        "skip logical steps. Use formal academic prose."
    ),
    "creative": (
        "You are Nexus Core, a creative and explanatory AI assistant. "
        "Use vivid analogies, real-world examples, and an engaging tone. "
        "Make complex ideas feel approachable without sacrificing accuracy."
    ),
    "technical": (
        "You are Nexus Core, a senior software engineer and technical expert. "
        "Provide exact, runnable code. Explain implementation decisions. "
        "Prefer depth over breadth. Never omit error handling in code examples."
    ),
    "tutor": (
        "You are Nexus Core, a patient and encouraging personal tutor. "
        "Your mission is to help the student UNDERSTAND, not just get the answer. "
        "Break every concept into first principles. Ask a clarifying question "
        "at the end if the topic warrants it. Use numbered steps for procedures."
    ),
}


# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_document():
    ai_client, err = _check_client()
    if err:
        return err

    uploaded_file = request.files.get("file")
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"status": "error", "message": "No file provided."})

    if not uploaded_file.filename.lower().endswith(".pdf"):
        return jsonify({"status": "error", "message": "Only PDF files are supported."})

    filename = uploaded_file.filename
    try:
        print(f"[Nexus RAG] Extracting: {filename}", file=sys.stderr)
        text = _extract_pdf_text(uploaded_file)
        if not text.strip():
            return jsonify({
                "status": "error",
                "message": "No text could be extracted. The PDF may be a scanned image."
            })

        chunks = _chunk_text(text)
        print(f"[Nexus RAG] {len(chunks)} chunks from '{filename}'", file=sys.stderr)

        embeddings = _embed(chunks)

        rag_store["chunks"].extend(chunks)
        rag_store["embeddings"].extend(embeddings)
        rag_store["doc_names"].extend([filename] * len(chunks))
        if filename not in rag_store["loaded_docs"]:
            rag_store["loaded_docs"].append(filename)

        return jsonify({
            "status": "success",
            "message": f"Loaded {len(chunks)} chunks from '{filename}'.",
            "loaded_docs": rag_store["loaded_docs"],
            "total_chunks": len(rag_store["chunks"]),
        })

    except Exception as exc:
        print(f"[Nexus RAG] Upload error: {exc}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(exc)})


@app.route("/knowledge-base", methods=["GET"])
def knowledge_base_status():
    return jsonify({
        "loaded_docs":  rag_store["loaded_docs"],
        "total_chunks": len(rag_store["chunks"]),
    })


@app.route("/knowledge-base/clear", methods=["POST"])
def clear_knowledge_base():
    rag_store["chunks"].clear()
    rag_store["embeddings"].clear()
    rag_store["doc_names"].clear()
    rag_store["loaded_docs"].clear()
    return jsonify({"status": "success", "message": "Knowledge base cleared."})


@app.route("/process", methods=["POST"])
def process_directive():
    print("[Nexus] /process request received", file=sys.stderr)

    ai_client, err = _check_client()
    if err:
        return err

    prompt_text = (request.form.get("prompt", "") or "").strip()
    tone_key    = request.form.get("tone", "analytical")
    try:
        temperature = float(request.form.get("temperature", 0.7))
        temperature = max(0.0, min(2.0, temperature))
    except ValueError:
        temperature = 0.7
    try:
        top_p = float(request.form.get("top_p", 0.9))
        top_p = max(0.0, min(1.0, top_p))
    except ValueError:
        top_p = 0.9

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
        except Exception as exc:
            print(f"[Nexus RAG] Retrieval error: {exc}", file=sys.stderr)

    parts = []
    if rag_context:
        parts.append(
            "RELEVANT EXCERPTS FROM YOUR KNOWLEDGE BASE:\n"
            "─────────────────────────────────────────\n"
            + rag_context +
            "\n─────────────────────────────────────────\n"
            "Answer using the excerpts above as your PRIMARY source. "
            "If the answer is not in the excerpts, say so and answer from general knowledge."
        )
    if document_text:
        parts.append(f"--- UPLOADED DOCUMENT ---\n{document_text}\n--- END DOCUMENT ---")
    if prompt_text:
        parts.append(prompt_text)
    else:
        parts.append("Provide a comprehensive summary of the document above.")

    user_message = "\n\n".join(parts)

    try:
        print(f"[Nexus] Calling gpt-4o | tone={tone_key} temp={temperature} rag={rag_context is not None}", file=sys.stderr)
        response = ai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            temperature=temperature,
            top_p=top_p,
            max_tokens=4096,
        )
        answer = response.choices[0].message.content
        return jsonify({
            "status": "success",
            "response": answer,
            "rag_active": rag_context is not None,
        })

    except Exception as exc:
        print(f"[Nexus] OpenAI error: {exc}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(exc)})


@app.route("/study", methods=["POST"])
def study_mode():
    print("[Nexus] /study request received", file=sys.stderr)

    ai_client, err = _check_client()
    if err:
        return err

    data       = request.get_json(silent=True) or {}
    mode       = data.get("mode", "explain")
    subject    = data.get("subject", "")
    content    = data.get("content", "")
    question   = data.get("question", "")
    difficulty = data.get("difficulty", "intermediate")

    base_system = TONE_PROFILES["tutor"]

    MODE_INSTRUCTIONS = {
        "explain": (
            "The student wants a clear explanation. Break it into first principles. "
            "Use analogies. End with a 1-sentence key takeaway."
        ),
        "quiz": (
            "Generate 5 multiple-choice quiz questions on the topic. "
            "Format each as:\nQ[n]: <question>\nA) ... B) ... C) ... D) ...\nAnswer: <letter>\nExplanation: <why>\n"
        ),
        "flashcards": (
            "Generate 8 flashcard pairs on the topic. "
            "Format as:\nFRONT: <term or question>\nBACK: <definition or answer>\n---\n"
            "Cover the most important facts, formulas, and concepts."
        ),
        "summarize": (
            "Produce a structured study summary: key concepts, important formulas or facts, "
            "common misconceptions to avoid, and 3 practice questions with answers."
        ),
        "exam_prep": (
            "Act as an exam coach. Identify the highest-probability topics to appear on an exam "
            "for this subject. List them ranked by importance. Then give a rapid-fire drill: "
            "10 short-answer questions with model answers."
        ),
    }

    mode_instruction = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS["explain"])
    system_prompt = f"{base_system}\n\nCurrent mode: {mode.upper()}.\n{mode_instruction}"
    if difficulty:
        system_prompt += f"\n\nPitch the difficulty level at: {difficulty} (beginner / intermediate / advanced)."

    rag_context = None
    rag_query   = subject or question or (content[:200] if content else "")
    if rag_query and rag_store["chunks"]:
        try:
            rag_context = _retrieve_context(rag_query)
        except Exception as exc:
            print(f"[Nexus RAG] Study retrieval error: {exc}", file=sys.stderr)

    parts = []
    if rag_context:
        parts.append(
            "RELEVANT EXCERPTS FROM KNOWLEDGE BASE:\n"
            + rag_context +
            "\nUse these excerpts to ground your response in the student's actual materials."
        )
    if subject:
        parts.append(f"Subject / Topic: {subject}")
    if content:
        parts.append(f"Material to work with:\n{content}")
    if question:
        parts.append(f"Student question: {question}")

    if not parts:
        return jsonify({"status": "error", "message": "Please provide a subject, content, or question."})

    user_message = "\n\n".join(parts)

    try:
        response = ai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            temperature=0.5,
            top_p=0.9,
            max_tokens=4096,
        )
        answer = response.choices[0].message.content
        return jsonify({
            "status": "success",
            "response": answer,
            "rag_active": rag_context is not None,
        })

    except Exception as exc:
        print(f"[Nexus] Study OpenAI error: {exc}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(exc)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
