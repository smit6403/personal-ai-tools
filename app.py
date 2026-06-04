import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from openai import OpenAI
import PyPDF2

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB Max Upload
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'md'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize OpenAI client (Expects OPENAI_API_KEY environment variable)
# To use a local model via Ollama instead, change base_url to "http://localhost:11434/v1"
client = OpenAI()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(filepath, extension):
    text = ""
    if extension == 'txt' or extension == 'md':
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
    elif extension == 'pdf':
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
    return text

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/query', methods=['POST'])
def query_ai():
    data = request.form
    user_prompt = data.get('prompt', '')
    tone = data.get('tone', 'balanced')
    creativity = float(data.get('creativity', 0.7))
    variance = float(data.get('variance', 0.9))
    
    file_context = ""
    
    # Handle File Upload if present
    if 'file' in request.files:
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            ext = filename.rsplit('.', 1)[1].lower()
            file_context = extract_text_from_file(filepath, ext)
            # Clean up file after reading
            os.remove(filepath)

    # Construct the system persona instructions
    system_instruction = (
        "You are an expert personal AI assistant optimized for deep analysis and academic clarity. "
        f"The user wants the response delivered in a {tone} tone. "
        "When generating creative text, avoid stereotypical patterns, repetitive vocabulary, "
        "and overused transitions. Vary your sentence structures, length, and cadence naturally."
    )

    # Construct final message context
    user_message = user_prompt
    if file_context:
        user_message = f"Context from uploaded document:\n{file_context}\n\nUser Question:\n{user_prompt}"

    try:
        # Use gpt-4o or exchange with your preferred local model string if using Ollama (e.g., "llama3")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message}
            ],
            temperature=creativity,
            top_p=variance
        )
        ai_output = response.choices[0].message.content
        return jsonify({"success": True, "response": ai_output})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    app.run(debug=True)