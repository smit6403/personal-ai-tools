/**
 * NEXUS // CORE AI — main.js
 * Completely rebuilt. Defensive, readable, zero silent failures.
 */
 
(function () {
  "use strict";
 
  /* ================================================================
     WAIT FOR DOM
  ================================================================ */
  document.addEventListener("DOMContentLoaded", init);
 
  function init() {
    console.log("[Nexus] DOM ready — wiring subsystems");
 
    /* ── Element references ─────────────────────────────────── */
    const statusBadge     = document.getElementById("system-status");
 
    // Tab switching
    const tabBtns         = document.querySelectorAll(".tab-btn");
    const panelGeneral    = document.getElementById("panel-general");
    const panelStudy      = document.getElementById("panel-study");
    const inputGeneral    = document.getElementById("input-general");
    const inputStudy      = document.getElementById("input-study");
 
    // General panel
    const tempSlider      = document.getElementById("temperature");
    const tempVal         = document.getElementById("temp-val");
    const topPSlider      = document.getElementById("top_p");
    const topPVal         = document.getElementById("topp-val");
    const toneSelect      = document.getElementById("tone");
    const dropZone        = document.getElementById("drop-zone");
    const fileInput       = document.getElementById("file-input");
    const fileStatus      = document.getElementById("file-status");
    const dropHint        = document.getElementById("drop-hint");
    const clearFileBtn    = document.getElementById("clear-file");
    const promptTextarea  = document.getElementById("prompt-input");
    const executeBtn      = document.getElementById("execute-btn");
 
    // Study panel
    const studyModeSelect = document.getElementById("study-mode");
    const studySubject    = document.getElementById("study-subject");
    const diffSlider      = document.getElementById("difficulty");
    const diffVal         = document.getElementById("diff-val");
    const studyContent    = document.getElementById("study-content");
    const studyQuestion   = document.getElementById("study-question");
    const studyBtn        = document.getElementById("study-btn");
 
    // Output
    const outputDisplay   = document.getElementById("output-display");
 
    /* ================================================================
       GUARD — if a critical element is missing, log and stop
    ================================================================ */
    const criticals = { outputDisplay, executeBtn, studyBtn };
    for (const [name, el] of Object.entries(criticals)) {
      if (!el) {
        console.error(`[Nexus] CRITICAL: element "${name}" not found in DOM`);
        return;
      }
    }
 
    /* ================================================================
       TAB SWITCHING
    ================================================================ */
    tabBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        const tab = btn.dataset.tab;
 
        // Update button states
        tabBtns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
 
        // Toggle panels & input bars
        if (tab === "general") {
          panelGeneral.classList.add("active");
          panelStudy.classList.remove("active");
          inputGeneral.classList.remove("hidden");
          inputStudy.classList.add("hidden");
        } else {
          panelStudy.classList.add("active");
          panelGeneral.classList.remove("active");
          inputStudy.classList.remove("hidden");
          inputGeneral.classList.add("hidden");
        }
      });
    });
 
    /* ================================================================
       SLIDERS
    ================================================================ */
    function wireSlider(slider, display, formatter) {
      if (!slider || !display) return;
      slider.addEventListener("input", () => {
        display.textContent = formatter(slider.value);
      });
    }
 
    wireSlider(tempSlider, tempVal, v => parseFloat(v).toFixed(1));
    wireSlider(topPSlider, topPVal, v => parseFloat(v).toFixed(2));
    wireSlider(diffSlider, diffVal, v => {
      return ["Beginner", "Intermediate", "Advanced"][parseInt(v, 10)] || "Intermediate";
    });
 
    /* ================================================================
       FILE UPLOAD
    ================================================================ */
    function markFileLoaded(file) {
      if (!file) return;
      const kb = (file.size / 1024).toFixed(1);
      fileStatus.textContent = `✓ ${file.name} (${kb} KB)`;
      dropHint.textContent   = "Document loaded";
      dropZone.classList.add("loaded");
      clearFileBtn.classList.remove("hidden");
    }
 
    function clearFile() {
      fileInput.value          = "";
      fileStatus.textContent   = "No file loaded";
      dropHint.textContent     = "Drag & drop or click to browse";
      dropZone.classList.remove("loaded");
      clearFileBtn.classList.add("hidden");
    }
 
    // The hidden <input type="file"> sits inside the drop zone and captures clicks naturally.
    fileInput.addEventListener("change", () => {
      if (fileInput.files.length > 0) markFileLoaded(fileInput.files[0]);
    });
 
    // Drag & drop
    dropZone.addEventListener("dragover", e => {
      e.preventDefault();
      dropZone.classList.add("drag-over");
    });
    dropZone.addEventListener("dragleave", () => {
      dropZone.classList.remove("drag-over");
    });
    dropZone.addEventListener("drop", e => {
      e.preventDefault();
      dropZone.classList.remove("drag-over");
      const files = e.dataTransfer.files;
      if (files.length > 0) {
        // Transfer dropped files into the input element
        try {
          const dt = new DataTransfer();
          dt.items.add(files[0]);
          fileInput.files = dt.files;
          markFileLoaded(files[0]);
        } catch (_) {
          // DataTransfer not supported in some browsers — graceful degradation
          fileStatus.textContent = `${files[0].name} (dropped — click Browse to re-select)`;
          dropZone.classList.add("loaded");
        }
      }
    });
 
    clearFileBtn.addEventListener("click", clearFile);
 
    /* ================================================================
       OUTPUT HELPERS
    ================================================================ */
    function setStatus(state) {
      if (!statusBadge) return;
      statusBadge.className = "status-badge";
      if (state === "computing") {
        statusBadge.classList.add("computing");
        statusBadge.textContent = "COMPUTING";
      } else if (state === "error") {
        statusBadge.classList.add("error");
        statusBadge.textContent = "ERROR";
      } else {
        statusBadge.textContent = "ONLINE";
      }
    }
 
    function showLoading(msg) {
      outputDisplay.innerHTML = `<div class="loading-msg">${msg}</div>`;
    }
 
    function showError(msg) {
      outputDisplay.innerHTML = `<div class="error-msg"><strong>[ERROR]</strong> ${escapeHtml(msg)}</div>`;
    }
 
    function showMarkdown(text) {
      try {
        const html = marked.parse(text);
        outputDisplay.innerHTML = `<div class="response-body">${html}</div>`;
      } catch (_) {
        // Fallback: plain text with line breaks
        outputDisplay.innerHTML = `<div class="response-body">${escapeHtml(text).replace(/\n/g, "<br>")}</div>`;
      }
      outputDisplay.scrollTop = 0;
    }
 
    function escapeHtml(str) {
      return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    }
 
    function lockUI(btn, label) {
      btn.disabled = true;
      btn.querySelector(".exec-label").textContent = label;
    }
 
    function unlockUI(btn, label) {
      btn.disabled = false;
      btn.querySelector(".exec-label").textContent = label;
    }
 
    /* ================================================================
       GENERAL EXECUTE
    ================================================================ */
    executeBtn.addEventListener("click", async () => {
      const prompt   = promptTextarea.value.trim();
      const hasFile  = fileInput.files.length > 0;
 
      if (!prompt && !hasFile) {
        alert("Please enter a prompt or upload a PDF before executing.");
        return;
      }
 
      lockUI(executeBtn, "...");
      setStatus("computing");
      showLoading("[PROCESSING] Sending request to gpt-4o…");
 
      const formData = new FormData();
      formData.append("prompt",      prompt);
      formData.append("tone",        toneSelect.value);
      formData.append("temperature", tempSlider.value);
      formData.append("top_p",       topPSlider.value);
      if (hasFile) formData.append("file", fileInput.files[0]);
 
      try {
        const res = await fetch("/process", { method: "POST", body: formData });
 
        if (!res.ok) throw new Error(`Server returned HTTP ${res.status}`);
 
        const data = await res.json();
 
        if (data.status === "success") {
          showMarkdown(data.response);
          setStatus("online");
        } else {
          showError(data.message || "Unknown error from server.");
          setStatus("error");
        }
      } catch (err) {
        showError(
          `Connection failed: ${err.message}\n\n` +
          "• Check your OpenAI API key in Render → Environment Variables.\n" +
          "• If Render just deployed, wait 30 seconds and refresh."
        );
        setStatus("error");
        console.error("[Nexus] Fetch error:", err);
      } finally {
        unlockUI(executeBtn, "EXECUTE");
        // Do NOT clear the textarea — user may want to refine the same prompt
      }
    });
 
    /* ================================================================
       STUDY EXECUTE
    ================================================================ */
    studyBtn.addEventListener("click", async () => {
      const question = studyQuestion.value.trim();
      const subject  = studySubject ? studySubject.value.trim() : "";
      const content  = studyContent ? studyContent.value.trim() : "";
 
      if (!subject && !content && !question) {
        alert("Please enter a subject, paste some notes, or ask a question.");
        return;
      }
 
      const diffMap  = ["beginner", "intermediate", "advanced"];
      const difficulty = diffMap[parseInt(diffSlider.value, 10)] || "intermediate";
 
      lockUI(studyBtn, "...");
      setStatus("computing");
      showLoading("[STUDY MODE] Generating response…");
 
      const payload = {
        mode:       studyModeSelect.value,
        subject,
        content,
        question,
        difficulty,
      };
 
      try {
        const res = await fetch("/study", {
          method:  "POST",
          headers: { "Content-Type": "application/json" },
          body:    JSON.stringify(payload),
        });
 
        if (!res.ok) throw new Error(`Server returned HTTP ${res.status}`);
 
        const data = await res.json();
 
        if (data.status === "success") {
          showMarkdown(data.response);
          setStatus("online");
        } else {
          showError(data.message || "Unknown error from server.");
          setStatus("error");
        }
      } catch (err) {
        showError(`Connection failed: ${err.message}`);
        setStatus("error");
        console.error("[Nexus] Study fetch error:", err);
      } finally {
        unlockUI(studyBtn, "STUDY");
      }
    });
 
    /* ================================================================
       KEYBOARD SHORTCUT: Ctrl+Enter / Cmd+Enter to submit
    ================================================================ */
    function handleSubmitShortcut(e, btn) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        if (!btn.disabled) btn.click();
      }
    }
    promptTextarea.addEventListener("keydown", e => handleSubmitShortcut(e, executeBtn));
    studyQuestion.addEventListener("keydown",  e => handleSubmitShortcut(e, studyBtn));
 
    console.log("[Nexus] All subsystems online ✓");
  }
 
})();
 
