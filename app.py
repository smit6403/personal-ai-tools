import os
import sys
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Safely extract the secret OpenAI API token from the secure cloud layer
openai_api_token = os.environ.get("OPENAI_API_KEY")

# Initialize the structural OpenAI engine asset
client = OpenAI(api_key=openai_api_token)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_directive():
    print(":: Nexus Core Engine: Inbound payload transmission detected.", file=sys.stderr)
    try:
        # 1. Structural Environment Verification
        if not openai_api_token or openai_api_token.strip() == "":
            print(" -> ERROR: API security key is missing or blank.", file=sys.stderr)
            return jsonify({
                'status': 'error', 
                'message': 'API Key access failure. Ensure OPENAI_API_KEY is correctly stored inside Render Environment settings.'
            })

        # 2. Extract Variable Packets from Frontend Form
        prompt_input = request.form.get('prompt', '').strip()
        tone_profile = request.form.get('tone', 'Analytical & Academic')
        temperature_setting = float(request.form.get('temperature', 0.7))
        topp_setting = float(request.form.get('top_p', 0.9))
        
        print(f" -> Parameters Engaged: Tone='{tone_profile}' | Temp={temperature_setting} | TopP={topp_setting}", file=sys.stderr)
        
        document_text_pool = ""
        
        # 3. Handle File Extraction via Staged Uploads
        if 'file' in request.files:
            uploaded_file = request.files['file']
            if uploaded_file and uploaded_file.filename != '':
                print(f" -> File detected for ingestion: '{uploaded_file.filename}'", file=sys.stderr)
                try:
                    pdf_processing_reader = PdfReader(uploaded_file)
                    extracted_pages_count = len(pdf_processing_reader.pages)
                    
                    for page_index in range(extracted_pages_count):
                        target_page = pdf_processing_reader.pages[page_index]
                        page_text_content = target_page.extract_text()
                        if page_text_content:
                            document_text_pool += page_text_content + "\n"
                            
                    print(f" -> Document Ingestion Success: Mapped {extracted_pages_count} pages.", file=sys.stderr)
                except Exception as file_read_error:
                    print(f" -> CRITICAL: File extraction interrupted: {str(file_read_error)}", file=sys.stderr)
                    return jsonify({
                        'status': 'error', 
                        'message': f'Document Ingestion Failure (Internal File Error): {str(file_read_error)}'
                    })

        # 4. Fail-Safe Verification for Empty Requests
        if not prompt_input and not document_text_pool:
            print(" -> Warning: Action halted due to vacant payload fields.", file=sys.stderr)
            return jsonify({
                'status': 'error', 
                'message': 'Execution halted: You must either input a text prompt or upload a reference file matrix to begin processing.'
            })

        # 5. Build High-Accuracy System Matrix Prompts
        system_architecture_framework = (
            f"You are Nexus Core, an omni-capable, elite reasoning engine possessing maximum analytical authority. "
            f"Your processing protocols are tuned to deliver comprehensive, deeply accurate, and meticulously structured solutions. "
            f"When answering questions based on ingested materials, cross-reference data points aggressively to maintain absolute factual grounding. "
            f"Never shorten mathematical or programmatic logic steps. Your mandatory phrasing profile is: '{tone_profile}'."
        )
        
        # Assemble user request using structural boundary constraints
        structured_user_payload = ""
        if document_text_pool:
            structured_user_payload += f"--- START INGESTED REFERENCE CORE MATERIALS ---\n{document_text_pool}\n--- END INGESTED REFERENCE CORE MATERIALS ---\n\n"
        
        structured_user_payload += f"[OPERATIONAL DIRECTIVE]: {prompt_input if prompt_input else 'Analyze the provided materials comprehensively and extract core insights.'}"

        print(" -> Requesting generation via flagship gpt-4o framework...", file=sys.stderr)
        
        # 6. Execute Generation via Flagship OpenAI Model Architecture
        api_generation_sequence = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_architecture_framework},
                {"role": "user", "content": structured_user_payload}
            ],
            temperature=temperature_setting,
            top_p=topp_setting
        )
        
        finalized_ai_solution = api_generation_sequence.choices[0].message.content
        print(" -> Solution successfully generated. Dispatching packet back to terminal layout.", file=sys.stderr)
        
        return jsonify({
            'status': 'success', 
            'response': finalized_ai_solution
        })

    except Exception as matrix_global_fault:
        print(f" -> CRITICAL EXCEPTION IN ENGINE: {str(matrix_global_fault)}", file=sys.stderr)
        return jsonify({
            'status': 'error', 
            'message': f'Core System Exception Interrupted Generation: {str(matrix_global_fault)}'
        })

if __name__ == '__main__':
    app.run(debug=True)
