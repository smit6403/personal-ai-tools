import os
import sys
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from pypdf import PdfReader
from dotenv import load_dotenv
 
load_dotenv()
 
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB upload limit
 
# ---------------------------------------------------------------------------
# OpenAI client — initialized once at startup
# ---------------------------------------------------------------------------
_api_key = os.environ.get("OPENAI_API_KEY", "")
client = OpenAI(api_key=_api_key) if _api_key else None
 
 
def _check_client():
    """Return (client, error_response). error_response is None when OK."""
    if not client:
        return None, jsonify({
            "status": "error",
            "message": "OPENAI_API_KEY is missing. Add it to Render → Environment Variables."
        })
    return client, None
 
 
def _extract_pdf_text(file_storage):
    """Extract all text from an uploaded PDF FileStorage object."""
    reader = PdfReader(file_storage)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)
 
 
# ---------------------------------------------------------------------------
# System prompt builder — used by both /process and /study endpoints
# ---------------------------------------------------------------------------
 
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
 
 
# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
 
@app.route("/")
def index():
    return render_template("index.html")
 
 
@app.route("/process", methods=["POST"])
def process_directive():
    """
    Main generation endpoint.
    Accepts multipart/form-data with optional PDF upload.
    """
    print("[Nexus] /process request received", file=sys.stderr)
 
    ai_client, err = _check_client()
    if err:
        return err
 
    # --- Extract form fields with safe defaults ---
    prompt_text   = (request.form.get("prompt", "") or "").strip()
    tone_key      = request.form.get("tone", "analytical")
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
 
    # --- PDF extraction ---
    document_text = ""
    uploaded_file = request.files.get("file")
    if uploaded_file and uploaded_file.filename:
        print(f"[Nexus] Extracting PDF: {uploaded_file.filename}", file=sys.stderr)
        try:
            document_text = _extract_pdf_text(uploaded_file)
            print(f"[Nexus] Extracted {len(document_text)} characters", file=sys.stderr)
        except Exception as exc:
            print(f"[Nexus] PDF error: {exc}", file=sys.stderr)
            return jsonify({"status": "error", "message": f"PDF extraction failed: {exc}"})
 
    # --- Validate that there is something to process ---
    if not prompt_text and not document_text:
        return jsonify({
            "status": "error",
            "message": "Please enter a prompt or upload a PDF document."
        })
 
    # --- Build user message ---
    user_message_parts = []
    if document_text:
        user_message_parts.append(
            f"--- DOCUMENT CONTENT START ---\n{document_text}\n--- DOCUMENT CONTENT END ---\n"
        )
    if prompt_text:
        user_message_parts.append(prompt_text)
    else:
        user_message_parts.append(
            "Please analyze the document above and provide a comprehensive summary "
            "of its key concepts, arguments, and important details."
        )
 
    user_message = "\n\n".join(user_message_parts)
 
    # --- Call OpenAI ---
    try:
        print(f"[Nexus] Calling gpt-4o | tone={tone_key} temp={temperature} top_p={top_p}", file=sys.stderr)
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
        print("[Nexus] Response generated successfully", file=sys.stderr)
        return jsonify({"status": "success", "response": answer})
 
    except Exception as exc:
        print(f"[Nexus] OpenAI error: {exc}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(exc)})
 
 
@app.route("/study", methods=["POST"])
def study_mode():
    """
    Study-mode endpoint — optimised for tutoring, Q&A, flashcards, and exam prep.
    Accepts JSON body: { mode, subject, content, question, difficulty }
    """
    print("[Nexus] /study request received", file=sys.stderr)
 
    ai_client, err = _check_client()
    if err:
        return err
 
    data = request.get_json(silent=True) or {}
    mode       = data.get("mode", "explain")       # explain | quiz | flashcards | summarize | exam_prep
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
 
    # Build user message
    user_parts = []
    if subject:
        user_parts.append(f"Subject / Topic: {subject}")
    if content:
        user_parts.append(f"Material to work with:\n{content}")
    if question:
        user_parts.append(f"Student question: {question}")
 
    if not user_parts:
        return jsonify({"status": "error", "message": "Please provide a subject, content, or question."})
 
    user_message = "\n\n".join(user_parts)
 
    try:
        print(f"[Nexus] Study call | mode={mode} difficulty={difficulty}", file=sys.stderr)
        response = ai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            temperature=0.5,   # lower temp = more reliable educational content
            top_p=0.9,
            max_tokens=4096,
        )
        answer = response.choices[0].message.content
        return jsonify({"status": "success", "response": answer})
 
    except Exception as exc:
        print(f"[Nexus] Study OpenAI error: {exc}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(exc)})
 
 
# ---------------------------------------------------------------------------
# Entry point (local dev only — Render uses gunicorn)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)
