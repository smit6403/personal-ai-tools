document.addEventListener('DOMContentLoaded', () => {
    console.log(":: Nexus Core OS: Initiating Interactive Subsystems...");

    // UI Document Mapping Nodes
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
    const systemStatus = document.getElementById('system-status');

    // --- 1. DYNAMIC SLIDER SYSTEMS (ISOLATED) ---
    try {
        if (tempSlider && tempVal) {
            tempSlider.addEventListener('input', (event) => {
                tempVal.textContent = parseFloat(event.target.value).toFixed(1);
            });
            console.log(" -> Temperature Matrix Mapping: Verified");
        }
    } catch (err) { console.error("Slider initialization faulted safely:", err); }

    try {
        if (topPSlider && topPVal) {
            topPSlider.addEventListener('input', (event) => {
                topPVal.textContent = parseFloat(event.target.value).toFixed(2);
            });
            console.log(" -> Variance Matrix Mapping: Verified");
        }
    } catch (err) { console.error("Slider initialization faulted safely:", err); }

    // --- 2. MULTIPART FILE INGESTION CONTROLS (ISOLATED) ---
    if (dropZone && fileInput) {
        dropZone.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });

        fileInput.addEventListener('change', (event) => {
            if (event.target.files.length > 0) {
                const targetFile = event.target.files[0];
                if (fileNameDisplay) {
                    fileNameDisplay.textContent = `LOADED: ${targetFile.name} (${(targetFile.size / 1024).toFixed(1)} KB)`;
                }
                if (dropText) dropText.textContent = "Document Core Primed";
                dropZone.classList.add('ingested');
                console.log(` -> Data Staging Sequence Locked: ${targetFile.name}`);
            }
        });

        dropZone.addEventListener('dragover', (event) => {
            event.preventDefault();
            dropZone.classList.add('dragging');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragging');
        });

        dropZone.addEventListener('drop', (event) => {
            event.preventDefault();
            dropZone.classList.remove('dragging');
            if (event.dataTransfer.files.length > 0) {
                fileInput.files = event.dataTransfer.files;
                const droppedFile = event.dataTransfer.files[0];
                if (fileNameDisplay) {
                    fileNameDisplay.textContent = `LOADED: ${droppedFile.name}`;
                }
                if (dropText) dropText.textContent = "Document Core Primed";
                dropZone.classList.add('ingested');
                console.log(` -> Data Dropped Sequence Locked: ${droppedFile.name}`);
            }
        });
    }

    // --- 3. THE GENERATION DRIVE CONTROLLER (BULLETPROOFED) ---
    if (executeBtn) {
        console.log(" -> Main Execute Button Connector: Verified and Attached");
        
        executeBtn.removeAttribute('disabled'); // Ensure button is active on boot
        
        executeBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            console.log(":: Click Registered. Starting generation cycle...");
            
            const internalPromptText = promptInput ? promptInput.value.trim() : "";
            const validationCheckHasFile = fileInput && fileInput.files.length > 0;

            // Enforce validation to protect server traffic
            if (!internalPromptText && !validationCheckHasFile) {
                alert('Action Terminated: Please input structural text or drop reference files.');
                return;
            }

            // Lock UI controls to completely secure thread process traffic
            executeBtn.disabled = true;
            executeBtn.textContent = 'PROCESSING...';
            if (systemStatus) {
                systemStatus.textContent = "COMPUTING MATRIX";
                systemStatus.style.borderColor = "#ff0033";
            }
            if (outputDisplay) {
                outputDisplay.innerHTML = `<p class="system-message processing-pulse">[STREAM INITIATED] Route linked... Transforming input parameters through gpt-4o brain matrix...</p>`;
            }

            // Build request object envelope data format
            const dynamicRequestForm = new FormData();
            dynamicRequestForm.append('prompt', internalPromptText);
            dynamicRequestForm.append('tone', toneSelect ? toneSelect.value : 'Analytical & Academic');
            dynamicRequestForm.append('temperature', tempSlider ? tempSlider.value : 0.7);
            dynamicRequestForm.append('top_p', topPSlider ? topPSlider.value : 0.9);
            
            if (validationCheckHasFile) {
                dynamicRequestForm.append('file', fileInput.files[0]);
                console.log(" -> Attached staged file stream data to payload.");
            }

            try {
                console.log(" -> Dispatching fetch package to endpoint node '/process'...");
                const serverTransaction = await fetch('/process', {
                    method: 'POST',
                    body: dynamicRequestForm
                });
                
                console.log(` -> Response metadata returned with status code: ${serverTransaction.status}`);
                if (!serverTransaction.ok) {
                    throw new Error(`Cloud node returned critical crash transaction code: ${serverTransaction.status}`);
                }
                
                const processResultData = await serverTransaction.json();
                console.log(" -> JSON packet extracted successfully:", processResultData.status);
                
                if (outputDisplay) {
                    if (processResultData.status === 'success') {
                        // Pass raw model outputs into the Markdown parser engine for flawless styling
                        let structuredHTMLOutput = processResultData.response;
                        if (typeof marked !== 'undefined' && marked.parse) {
                            structuredHTMLOutput = marked.parse(processResultData.response);
                        } else {
                            structuredHTMLOutput = processResultData.response.replace(/\n/g, '<br>');
                        }
                        
                        outputDisplay.innerHTML = `<div class="response-text">${structuredHTMLOutput}</div>`;
                        if (systemStatus) systemStatus.textContent = "SYSTEM READY";
                        console.log(":: Generation sequence finalized successfully.");
                    } else {
                        outputDisplay.innerHTML = `<div class="error-message">[SYSTEM CONFIGURATION CRASH]: ${processResultData.message}</div>`;
                        if (systemStatus) systemStatus.textContent = "CORE ERROR";
                    }
                }
            } catch (networkCommunicationFault) {
                if (outputDisplay) {
                    outputDisplay.innerHTML = `
                        <div class="error-message">
                            [TRANSMISSION DISCONNECTED]: Core engine server connection broke.<br><br>
                            Possible causes:<br>
                            1. Your OpenAI Account has run completely out of processing funds.<br>
                            2. Render environment is building updates. Refresh page in 30 seconds.
                        </div>`;
                }
                if (systemStatus) systemStatus.textContent = "NETWORK FAULT";
                console.error('Critical Network Engine Diagnostics Info:', networkCommunicationFault);
            } finally {
                executeBtn.disabled = false;
                executeBtn.textContent = 'EXECUTE REQUEST';
                if (promptInput) promptInput.value = ""; // Safely wipe textarea for next entry
                console.log(":: Cycle finished. Interface unlocked.");
            }
        });
    } else {
        console.error("CRITICAL ALIGNMENT FAULT: Element id 'execute-btn' could not be found in current DOM layout.");
    }
});
