document.addEventListener('DOMContentLoaded', () => {
    const creativitySlider = document.getElementById('creativity');
    const creativityVal = document.getElementById('creativity-val');
    const varianceSlider = document.getElementById('variance');
    const varianceVal = document.getElementById('variance-val');
    
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileStatus = document.getElementById('file-status');
    
    const submitBtn = document.getElementById('submit-btn');
    const promptInput = document.getElementById('prompt-input');
    const outputBox = document.getElementById('output-box');
    
    let activeFile = null;

    // Update Slider Labels Dynamically
    creativitySlider.addEventListener('input', (e) => {
        creativityVal.textContent = e.target.value;
    });
    
    varianceSlider.addEventListener('input', (e) => {
        varianceVal.textContent = e.target.value;
    });

    // File Trigger Logic
    dropZone.addEventListener('click', () => fileInput.click());
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            activeFile = e.target.files[0];
            fileStatus.textContent = `Target Loaded: ${activeFile.name}`;
        }
    });

    // Drag and Drop implementation
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--accent-neon)';
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.style.borderColor = 'var(--border-color)';
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--border-color)';
        if (e.dataTransfer.files.length > 0) {
            activeFile = e.dataTransfer.files[0];
            fileStatus.textContent = `Target Loaded: ${activeFile.name}`;
        }
    });

    // Submission logic to backend API
    submitBtn.addEventListener('click', async () => {
        const textPrompt = promptInput.value.trim();
        if (!textPrompt && !activeFile) {
            alert('Please provide a prompt instruction or ingest a file target first.');
            return;
        }

        // Display User Action in Output Window
        const userDiv = document.createElement('div');
        userDiv.className = 'user-entry';
        userDiv.textContent = `> ${textPrompt || "[Document Processing Sequence Run]"}`;
        outputBox.appendChild(userDiv);
        outputBox.scrollTop = outputBox.scrollHeight;

        // Build Multi-part Form Data payload
        const formData = new FormData();
        formData.append('prompt', textPrompt);
        formData.append('tone', document.getElementById('tone').value);
        formData.append('creativity', creativitySlider.value);
        formData.append('variance', varianceSlider.value);
        if (activeFile) {
            formData.append('file', activeFile);
        }

        promptInput.value = '';
        submitBtn.disabled = true;
        submitBtn.textContent = 'PROCESSING...';

        try {
            const response = await fetch('/api/query', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            const aiDiv = document.createElement('div');
            aiDiv.className = 'ai-entry';

            if (data.success) {
                // Formatting backticks/newlines basic simulation
                aiDiv.innerHTML = data.response.replace(/\n/g, '<br>');
            } else {
                aiDiv.textContent = `SYSTEM ERROR: ${data.error}`;
                aiDiv.style.color = 'var(--accent-alert)';
            }

            outputBox.appendChild(aiDiv);
        } catch (err) {
            const errDiv = document.createElement('div');
            errDiv.className = 'ai-entry';
            errDiv.textContent = `CRITICAL MAIN LINK FAULT: ${err.message}`;
            errDiv.style.color = 'var(--accent-alert)';
            outputBox.appendChild(errDiv);
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'EXECUTE REQUEST';
            // Clear used file targets
            activeFile = null;
            fileInput.value = '';
            fileStatus.textContent = 'No file selected';
            outputBox.scrollTop = outputBox.scrollHeight;
        }
    });
});
