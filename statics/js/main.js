document.addEventListener('DOMContentLoaded', () => {
    // Target UI Elements
    const tempSlider = document.getElementById('temperature');
    const tempVal = document.getElementById('temp-val');
    const topPSlider = document.getElementById('top_p');
    const topPVal = document.getElementById('topp-val');
    
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileNameDisplay = document.getElementById('file-name');
    const dropText = document.getElementById('drop-text');
    
    const executeBtn = document.getElementById('execute-btn');
    const promptInput = document.getElementById('prompt-input');
    const outputDisplay = document.getElementById('output-display');
    const toneSelect = document.getElementById('tone');

    // 1. Live Sliders Functionality
    if (tempSlider && tempVal) {
        tempSlider.addEventListener('input', (e) => {
            tempVal.textContent = parseFloat(e.target.value).toFixed(1);
        });
    }

    if (topPSlider && topPVal) {
        topPSlider.addEventListener('input', (e) => {
            topPVal.textContent = parseFloat(e.target.value).toFixed(2);
        });
    }

    // 2. Clickable Drag-and-Drop Ingestion Mechanics
    if (dropZone && fileInput) {
        dropZone.addEventListener('click', () => {
            fileInput.click();
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                const name = e.target.files[0].name;
                if (fileNameDisplay) fileNameDisplay.textContent = name;
                if (dropText) dropText.textContent = "Document Loaded";
                dropZone.style.borderColor = "#ff0033";
            }
        });
    }

    // 3. Core Generation Engine Trigger Execution
    if (executeBtn) {
        executeBtn.addEventListener('click', async () => {
            const promptValue = promptInput ? promptInput.value.trim() : "";
            const hasFile = fileInput && fileInput.files.length > 0;

            if (!promptValue && !hasFile) {
                alert('System Action Halted: Enter a prompt request or load a PDF matrix document first.');
                return;
            }

            // Lock interface items during connection processing
            executeBtn.disabled = true;
            executeBtn.textContent = 'PROCESSING...';
            if (outputDisplay) {
                outputDisplay.innerHTML = `<p class="system-message processing-state">Processing request through upgraded intelligence matrix...</p>`;
            }

            const formData = new FormData();
            formData.append('prompt', promptValue);
            formData.append('tone', toneSelect ? toneSelect.value : 'Analytical & Academic');
            formData.append('temperature', tempSlider ? tempSlider.value : 0.7);
            formData.append('top_p', topPSlider ? topPSlider.value : 0.9);
            
            if (hasFile) {
                formData.append('file', fileInput.files[0]);
            }

            try {
                const fetchTarget = '/process';
                const connection = await fetch(fetchTarget, {
                    method: 'POST',
                    body: formData
                });
                
                const data = await connection.json();
                
                if (outputDisplay) {
                    if (data.status === 'success') {
                        // Converts simple newlines into HTML paragraphs for reading layout
                        const structuredOutput = data.response.replace(/\n/g, '<br>');
                        outputDisplay.innerHTML = `<div class="response-text">${structuredOutput}</div>`;
                    } else {
                        outputDisplay.innerHTML = `<p class="error-message">SYSTEM CRITICAL FAULT: ${data.message}</p>`;
                    }
                }
            } catch (networkError) {
                if (outputDisplay) {
                    outputDisplay.innerHTML = `<p class="error-message">CONNECTION FAULT: Core engine communication lost. Verify your OpenAI account funds balance.</p>`;
                }
                console.error('Core Transmission Error:', networkError);
            } finally {
                executeBtn.disabled = false;
                executeBtn.textContent = 'EXECUTE REQUEST';
            }
        });
    }
});
