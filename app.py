import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Initialize the OpenAI client securely using the environment variable
openai_api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_request():
    try:
        # 1. Verify API Key exists
        if not openai_api_key:
            return jsonify({'status': 'error', 'message': 'OpenAI API Key is missing from cloud environment settings.'})

        # 2. Extract configuration and inputs
        prompt = request.form.get('prompt', '').strip()
        tone = request.form.get('tone', 'Analytical & Academic')
        temperature = float(request.form.get('temperature', 0.7))
        top_p = float(request.form.get('top_p', 0.9))
        
        extracted_text = ""
        
        # 3. Handle PDF processing if a file was attached
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                try:
                    reader = PdfReader(file)
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            extracted_text += text + "\n"
                except Exception as pdf_err:
                    return jsonify({'status': 'error', 'message': f'Failed reading PDF file: {str(pdf_err)}'})

        # 4. Fallback validation if everything is empty
        if not prompt and not extracted_text:
            return jsonify({'status': 'error', 'message': 'No input prompt or file content was provided.'})

        # 5. Build system instructions and payload
        system_instruction = f"You are Nexus Core, a highly intelligent AI assistant. Style your output using a strict '{tone}' delivery system. Format responses beautifully with clean spacing."
        
        user_message = ""
        if extracted_text:
            user_message += f"[INGESTED DOCUMENT DATA]:\n{extracted_text}\n\n"
        user_message += f"[USER REQUEST]: {prompt}"

        # 6. Fetch processing generation from flagship model
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
        return jsonify({'status': 'error', 'message': f'Server Matrix Error: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True)
