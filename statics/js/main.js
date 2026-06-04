document.addEventListener('DOMContentLoaded', () => {
    const tempSlider = document.getElementById('temperature');
    const tempVal = document.getElementById('temp-val');
    const topPSlider = document.getElementById('top_p');
    const topPVal = document.getElementById('topp-val');
    
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileNameDisplay = document.getElementById('file-name');
    
    const executeBtn = document.getElementById('execute-btn');
    const promptInput = document.getElementById('prompt-input');
    const outputDisplay = document.getElementById('output-display');
    const toneSelect = document.getElementById('tone');

    // Make meters dynamically update their displayed values
    tempSlider.addEventListener('input', (e) => {
        tempVal.textContent = e.target.value;
    });

    topPSlider.addEventListener('input', (e) => {
        topPVal.textContent = e.target.value;
    });

    // File Upload handling
    dropZone.addEventListener('click', () => fileInput.click());
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            fileNameDisplay.textContent = e.target.files[0].name;
            fileNameDisplay.classList.add('active');
        }
    });

    // Execute Request Logic
    executeBtn.addEventListener('click', async () => {
        const prompt = promptInput.value.trim();
        if (!prompt && !fileInput.files[0]) {
            alert('Please enter a prompt or upload a file first.');
            return;
        }

        // Show loading state
        executeBtn.disabled = true;
        executeBtn.textContent = 'PROCESSING...';
        outputDisplay.innerHTML = `<p class="system-message scanning">Processing request through upgraded intelligence matrix...</p>`;

        const formData = new FormData();
        formData.append('prompt', prompt);
        formData.append('tone', toneSelect.value);
        formData.append('temperature', tempSlider.value);
        formData.append('top_p', topPSlider.value);
        if (fileInput.files[0]) {
            formData.append('file', fileInput.files[0]);
        }

        try {
            const response = await fetch('/process', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                outputDisplay.innerHTML = `<div class="response-text">${data.response}</div>`;
            } else {
                outputDisplay.innerHTML = `<p class="error-message">SYSTEM FAULT: ${data.message}</p>`;
            }
        } catch (error) {
            outputDisplay.innerHTML = `<p class="error-message">CONNECTION FAULT: Unable to communicate with core matrix.</p>`;
            console.error(error);
        } finally {
            executeBtn.disabled = false;
            executeBtn.textContent = 'EXECUTE REQUEST';
        }
    });
});
