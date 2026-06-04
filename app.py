import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Initialize upgraded intelligence connection
# Render will automatically inject the secure variable from your account dashboard
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_request():
    try:
        prompt = request.form.get('prompt', '').strip()
        tone = request.form.get('tone', 'Analytical & Academic')
        
        # Read parameters dynamically from sliders
        temperature = float(request.form.get('temperature', 0.7))
        top_p = float(request.form.get('top_p', 0.9))
        
        extracted_text = ""
        
        # Handle file upload if present
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                reader = PdfReader(file)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        extracted_text += text + "\n"

        # Formulate system framework
        system_instruction = f"You are Nexus Core, a highly accurate, deep-reasoning, and authoritative AI asset. Format all structural outputs clearly. Adopt a strict '{tone}' delivery style."
        
        user_message = ""
        if extracted_text:
            user_message += f"[INGESTED MATERIALS]:\n{extracted_text}\n\n"
        user_message += f"[INSTRUCTION]: {prompt}"

        # Request generation via advanced flagship model
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message}
            ],
            temperature=temperature,
            top_p=top_p
        )
        
        ai_response = completion.choices[0].message.content
        return jsonify({'status': 'success', 'response': ai_response})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
