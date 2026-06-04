document.addEventListener("DOMContentLoaded", () => {

  const tabBtns       = document.querySelectorAll(".tab-btn");
  const panelGeneral  = document.getElementById("panel-general");
  const panelStudy    = document.getElementById("panel-study");
  const inputGeneral  = document.getElementById("input-general");
  const inputStudy    = document.getElementById("input-study");
  const systemStatus  = document.getElementById("system-status");
  const ragBadge      = document.getElementById("rag-badge");
  const outputDisplay = document.getElementById("output-display");
  const temperatureEl = document.getElementById("temperature");
  const tempVal       = document.getElementById("temp-val");
  const topPEl        = document.getElementById("top_p");
  const toppVal       = document.getElementById("topp-val");
  const toneEl        = document.getElementById("tone");
  const dropZone      = document.getElementById("drop-zone");
  const fileInput     = document.getElementById("file-input");
  const fileStatus    = document.getElementById("file-status");
  const clearFileBtn  = document.getElementById("clear-file");
  const kbDropZone    = document.getElementById("kb-drop-zone");
  const kbFileInput   = document.getElementById("kb-file-input");
  const kbUploadBtn   = document.getElementById("kb-upload-btn");
  const kbStatus      = document.getElementById("kb-status");
  const kbClearBtn    = document.getElementById("kb-clear-btn");
  const promptInput   = document.getElementById("prompt-input");
  const executeBtn    = document.getElementById("execute-btn");
  const studyModeEl   = document.getElementById("study-mode");
  const studySubject  = document.getElementById("study-subject");
  const difficultyEl  = document.getElementById("difficulty");
  const diffVal       = document.getElementById("diff-val");
  const studyContent  = document.getElementById("study-content");
  const studyQuestion = document.getElementById("study-question");
  const studyBtn      = document.getElementById("study-btn");

  let inlineFile    = null;
  let kbPendingFile = null;
  const DIFF_LABELS = ["Beginner", "Intermediate", "Advanced"];

  // ── Tabs ──────────────────────────────────────────────────────
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const tab = btn.dataset.tab;
      if (tab === "general") {
        panelGeneral && panelGeneral.classList.add("active");
        panelStudy   && panelStudy.classList.remove("active");
        inputGeneral && inputGeneral.classList.remove("hidden");
        inputStudy   && inputStudy.classList.add("hidden");
      } else {
        panelStudy   && panelStudy.classList.add("active");
        panelGeneral && panelGeneral.classList.remove("active");
        inputStudy   && inputStudy.classList.remove("hidden");
        inputGeneral && inputGeneral.classList.add("hidden");
      }
    });
  });

  // ── Sliders ───────────────────────────────────────────────────
  temperatureEl && temperatureEl.addEventListener("input", () => {
    if (tempVal) tempVal.textContent = parseFloat(temperatureEl.value).toFixed(1);
  });
  topPEl && topPEl.addEventListener("input", () => {
    if (toppVal) toppVal.textContent = parseFloat(topPEl.value).toFixed(2);
  });
  difficultyEl && difficultyEl.addEventListener("input", () => {
    if (diffVal) diffVal.textContent = DIFF_LABELS[parseInt(difficultyEl.value)] || "Intermediate";
  });

  // ── Inline PDF ────────────────────────────────────────────────
  function setInlineFile(file) {
    inlineFile = file;
    if (fileStatus)   fileStatus.textContent = file.name;
    if (dropZone)     dropZone.classList.add("loaded");
    if (clearFileBtn) clearFileBtn.classList.remove("hidden");
  }

  if (dropZone) {
    dropZone.addEventListener("dragover", e => { e.preventDefault(); dropZone.classList.add("drag-over"); });
    dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
    dropZone.addEventListener("drop", e => {
      e.preventDefault();
      dropZone.classList.remove("drag-over");
      const f = e.dataTransfer.files[0];
      if (f && f.name.toLowerCase().endsWith(".pdf")) setInlineFile(f);
    });
  }
  fileInput && fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) setInlineFile(fileInput.files[0]);
  });
  clearFileBtn && clearFileBtn.addEventListener("click", () => {
    inlineFile = null;
    if (fileInput)   fileInput.value = "";
    if (fileStatus)  fileStatus.textContent = "No file loaded";
    if (dropZone)    dropZone.classList.remove("loaded");
    clearFileBtn.classList.add("hidden");
  });

  // ── KB drop zone ──────────────────────────────────────────────
  function setKbPendingFile(file) {
    kbPendingFile = file;
    if (kbStatus)   kbStatus.textContent = `Ready to upload: ${file.name}`;
    if (kbDropZone) kbDropZone.classList.add("loaded");
  }

  if (kbDropZone) {
    kbDropZone.addEventListener("dragover", e => { e.preventDefault(); kbDropZone.classList.add("drag-over"); });
    kbDropZone.addEventListener("dragleave", () => kbDropZone.classList.remove("drag-over"));
    kbDropZone.addEventListener("drop", e => {
      e.preventDefault();
      kbDropZone.classList.remove("drag-over");
      const f = e.dataTransfer.files[0];
      if (f && f.name.toLowerCase().endsWith(".pdf")) setKbPendingFile(f);
    });
  }
  kbFileInput && kbFileInput.addEventListener("change", () => {
    if (kbFileInput.files[0]) setKbPendingFile(kbFileInput.files[0]);
  });

  // ── KB Upload ─────────────────────────────────────────────────
  kbUploadBtn && kbUploadBtn.addEventListener("click", async () => {
    if (!kbPendingFile) {
      if (kbStatus) kbStatus.textContent = "Drop a PDF first.";
      return;
    }
    kbUploadBtn.disabled = true;
    if (kbStatus) kbStatus.textContent = `Uploading ${kbPendingFile.name}…`;
    const fd = new FormData();
    fd.append("file", kbPendingFile);
    try {
      const res  = await fetch("/upload", { method: "POST", body: fd });
      const data = await res.json();
      if (data.status === "success") {
        if (kbStatus) kbStatus.textContent = `✓ ${data.message} | Total: ${data.total_chunks} chunks`;
        kbPendingFile = null;
        if (kbFileInput) kbFileInput.value = "";
        if (kbDropZone)  kbDropZone.classList.remove("loaded");
        updateKbList(data.loaded_docs);
        setRagActive(true);
        if (kbClearBtn) kbClearBtn.classList.remove("hidden");
      } else {
        if (kbStatus) kbStatus.textContent = `✗ ${data.message}`;
      }
    } catch (err) {
      if (kbStatus) kbStatus.textContent = `✗ Network error: ${err.message}`;
    } finally {
      kbUploadBtn.disabled = false;
    }
  });

  // ── KB Clear ──────────────────────────────────────────────────
  kbClearBtn && kbClearBtn.addEventListener("click", async () => {
    try {
      await fetch("/knowledge-base/clear", { method: "POST" });
      if (kbStatus) kbStatus.textContent = "Knowledge base cleared.";
      updateKbList([]);
      setRagActive(false);
      kbClearBtn.classList.add("hidden");
    } catch (err) {
      if (kbStatus) kbStatus.textContent = `✗ ${err.message}`;
    }
  });

  // ── Helpers ───────────────────────────────────────────────────
  function setRagActive(active) {
    if (!ragBadge) return;
    active ? ragBadge.classList.remove("hidden") : ragBadge.classList.add("hidden");
  }

  function updateKbList(docs) {
    const kbList = document.getElementById("kb-doc-list");
    if (!kbList) return;
    kbList.innerHTML = (docs && docs.length)
      ? docs.map(d => `<div class="kb-doc-item">📄 ${d}</div>`).join("")
      : "";
  }

  function setStatus(state) {
    if (!systemStatus) return;
    systemStatus.className = "status-badge";
    if (state === "computing") {
      systemStatus.classList.add("computing");
      systemStatus.textContent = "PROCESSING";
    } else if (state === "error") {
      systemStatus.classList.add("error");
      systemStatus.textContent = "ERROR";
    } else {
      systemStatus.textContent = "ONLINE";
    }
  }

  function showLoading(msg) {
    if (outputDisplay) outputDisplay.innerHTML = `<div class="loading-msg">[ ${msg} ]</div>`;
  }

  function showError(msg) {
    if (outputDisplay) outputDisplay.innerHTML =
      `<div class="error-msg"><strong>[ERROR]</strong><br/>${escapeHtml(msg)}</div>`;
  }

  function showResponse(text, ragUsed) {
    const parsed = (typeof marked !== "undefined")
      ? marked.parse(text)
      : `<pre>${escapeHtml(text)}</pre>`;
    const ragNote = ragUsed
      ? `<div class="rag-note">📚 ANSWER SOURCED FROM YOUR DOCUMENTS</div>`
      : "";
    if (outputDisplay) outputDisplay.innerHTML = `${ragNote}<div class="response-body">${parsed}</div>`;
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // ── EXECUTE ───────────────────────────────────────────────────
  executeBtn && executeBtn.addEventListener("click", async () => {
    const prompt = promptInput ? promptInput.value.trim() : "";
    if (!prompt && !inlineFile) {
      showError("Enter a prompt or upload a PDF before executing.");
      return;
    }
    executeBtn.disabled = true;
    setStatus("computing");
    showLoading("Processing directive…");

    const fd = new FormData();
    if (prompt)        fd.append("prompt",      prompt);
    if (toneEl)        fd.append("tone",         toneEl.value);
    if (temperatureEl) fd.append("temperature",  temperatureEl.value);
    if (topPEl)        fd.append("top_p",        topPEl.value);
    if (inlineFile)    fd.append("file",         inlineFile);

    try {
      const res  = await fetch("/process", { method: "POST", body: fd });
      const data = await res.json();
      if (data.status === "success") {
        setStatus("online");
        showResponse(data.response, data.rag_active);
        if (data.rag_active) setRagActive(true);
      } else {
        setStatus("error");
        showError(data.message || "Unknown error.");
      }
    } catch (err) {
      setStatus("error");
      showError(`Network error: ${err.message}`);
    } finally {
      executeBtn.disabled = false;
    }
  });

  promptInput && promptInput.addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      if (executeBtn && !executeBtn.disabled) executeBtn.click();
    }
  });

  // ── STUDY ─────────────────────────────────────────────────────
  studyBtn && studyBtn.addEventListener("click", async () => {
    const subject  = studySubject  ? studySubject.value.trim()  : "";
    const content  = studyContent  ? studyContent.value.trim()  : "";
    const question = studyQuestion ? studyQuestion.value.trim() : "";
    if (!subject && !content && !question) {
      showError("Enter a subject, paste some notes, or ask a question first.");
      return;
    }
    studyBtn.disabled = true;
    setStatus("computing");
    showLoading("Generating study material…");

    const diffIndex = difficultyEl ? parseInt(difficultyEl.value) : 1;
    const diffLabel = (DIFF_LABELS[diffIndex] || "Intermediate").toLowerCase();
    const payload = {
      mode: studyModeEl ? studyModeEl.value : "explain",
      subject, content, question,
      difficulty: diffLabel,
    };

    try {
      const res  = await fetch("/study", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.status === "success") {
        setStatus("online");
        showResponse(data.response, data.rag_active);
        if (data.rag_active) setRagActive(true);
      } else {
        setStatus("error");
        showError(data.message || "Unknown error.");
      }
    } catch (err) {
      setStatus("error");
      showError(`Network error: ${err.message}`);
    } finally {
      studyBtn.disabled = false;
    }
  });

  studyQuestion && studyQuestion.addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      if (studyBtn && !studyBtn.disabled) studyBtn.click();
    }
  });

  // ── Load KB state on page load ────────────────────────────────
  fetch("/knowledge-base")
    .then(r => r.json())
    .then(data => {
      if (data.loaded_docs && data.loaded_docs.length > 0) {
        updateKbList(data.loaded_docs);
        setRagActive(true);
        if (kbStatus) kbStatus.textContent =
          `${data.loaded_docs.length} doc(s) loaded — ${data.total_chunks} chunks`;
        if (kbClearBtn) kbClearBtn.classList.remove("hidden");
      }
    })
    .catch(() => {});

});
