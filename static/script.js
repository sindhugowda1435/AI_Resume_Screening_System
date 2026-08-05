(function () {
  "use strict";

  const jobDescriptionEl = document.getElementById("jobDescription");
  const resumeTextEl = document.getElementById("resumeText");
  const resumeFilesInput = document.getElementById("resumeFiles");
  const dropzone = document.getElementById("dropzone");
  const fileListEl = document.getElementById("fileList");
  const screenBtn = document.getElementById("screenBtn");
  const btnText = document.getElementById("btnText");
  const btnSpinner = document.getElementById("btnSpinner");
  const errorMsg = document.getElementById("errorMsg");
  const resultsSection = document.getElementById("resultsSection");
  const resultsList = document.getElementById("resultsList");
  const jobSkillsTags = document.getElementById("jobSkillsTags");
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");

  let selectedFiles = [];

  // ---------- Tabs ----------
  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabBtns.forEach((b) => b.classList.remove("active"));
      tabContents.forEach((c) => c.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
    });
  });

  // ---------- File handling ----------
  function renderFileList() {
    fileListEl.innerHTML = "";
    selectedFiles.forEach((file, idx) => {
      const li = document.createElement("li");
      const sizeKb = (file.size / 1024).toFixed(0);
      li.innerHTML = `<span>${escapeHtml(file.name)} <span style="color:var(--ink-soft)">(${sizeKb} KB)</span></span>`;
      const removeBtn = document.createElement("button");
      removeBtn.className = "remove-file";
      removeBtn.type = "button";
      removeBtn.textContent = "✕";
      removeBtn.addEventListener("click", () => {
        selectedFiles.splice(idx, 1);
        renderFileList();
      });
      li.appendChild(removeBtn);
      fileListEl.appendChild(li);
    });
  }

  function addFiles(fileList) {
    const incoming = Array.from(fileList);
    incoming.forEach((f) => {
      const alreadyAdded = selectedFiles.some(
        (existing) => existing.name === f.name && existing.size === f.size
      );
      if (!alreadyAdded) selectedFiles.push(f);
    });
    renderFileList();
  }

  resumeFilesInput.addEventListener("change", (e) => {
    addFiles(e.target.files);
    resumeFilesInput.value = "";
  });

  ["dragover", "dragenter"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    if (e.dataTransfer && e.dataTransfer.files) {
      addFiles(e.dataTransfer.files);
    }
  });

  // ---------- Submit ----------
  screenBtn.addEventListener("click", async () => {
    hideError();

    const jobText = jobDescriptionEl.value.trim();
    if (!jobText) {
      showError("Please paste a job description first.");
      return;
    }

    const activeTab = document.querySelector(".tab-btn.active").dataset.tab;
    const pastedResume = resumeTextEl.value.trim();

    if (activeTab === "upload" && selectedFiles.length === 0) {
      showError("Upload at least one resume file, or switch to Paste Text.");
      return;
    }
    if (activeTab === "paste" && !pastedResume) {
      showError("Paste resume text first, or switch to Upload Files.");
      return;
    }

    const formData = new FormData();
    formData.append("job_description", jobText);

    if (activeTab === "upload") {
      selectedFiles.forEach((f) => formData.append("resume_files", f));
    } else {
      formData.append("resume_text", pastedResume);
    }

    setLoading(true);
    try {
      const res = await fetch("/api/screen", { method: "POST", body: formData });
      const data = await res.json();

      if (!res.ok) {
        showError(data.error || "Something went wrong. Please try again.");
        return;
      }
      renderResults(data);
    } catch (err) {
      showError("Could not reach the server. Is the Flask app running?");
    } finally {
      setLoading(false);
    }
  });

  function setLoading(isLoading) {
    screenBtn.disabled = isLoading;
    btnSpinner.classList.toggle("hidden", !isLoading);
    btnText.textContent = isLoading ? "Screening..." : "Screen Resume(s)";
  }

  function showError(msg) {
    errorMsg.textContent = msg;
    errorMsg.classList.remove("hidden");
  }

  function hideError() {
    errorMsg.classList.add("hidden");
    errorMsg.textContent = "";
  }

  // ---------- Results rendering ----------
  function verdictClass(verdict) {
    if (verdict === "Strong Match") return "strong";
    if (verdict === "Moderate Match") return "moderate";
    if (verdict === "Weak Match") return "weak";
    return "poor";
  }

  function renderResults(data) {
    resultsList.innerHTML = "";
    jobSkillsTags.innerHTML = "";

    (data.job_skills || []).forEach((skill) => {
      const span = document.createElement("span");
      span.className = "job-skill-tag";
      span.textContent = skill;
      jobSkillsTags.appendChild(span);
    });

    data.results.forEach((r) => {
      const card = document.createElement("div");

      if (r.error) {
        card.className = "result-card error";
        card.innerHTML = `
          <div>
            <p class="result-filename">${escapeHtml(r.filename || "Unknown file")}</p>
            <p class="card-error-msg">⚠ ${escapeHtml(r.error)}</p>
          </div>`;
        resultsList.appendChild(card);
        return;
      }

      card.className = "result-card";

      const vClass = verdictClass(r.verdict);
      const contact = r.contact || {};
      const contactBits = [];
      if (contact.email) contactBits.push(`<span>✉ ${escapeHtml(contact.email)}</span>`);
      if (contact.phone) contactBits.push(`<span>☎ ${escapeHtml(contact.phone)}</span>`);
      if (contact.years_experience) contactBits.push(`<span><strong>${escapeHtml(contact.years_experience)}</strong> yrs exp.</span>`);

      card.innerHTML = `
        <div class="stamp ${vClass}">
          <span class="stamp-score">${r.final_score}%</span>
          <span class="stamp-label">${escapeHtml(r.verdict)}</span>
        </div>
        <div class="result-body">
          <p class="result-filename">${escapeHtml(r.filename)}</p>
          <div class="result-meta">${contactBits.join("")}</div>

          <div class="score-bars">
            ${scoreBarRow("Text Match", r.similarity_score)}
            ${scoreBarRow("Skill Match", r.keyword_score)}
          </div>

          <div class="skills-section">
            <h4>Matched Skills (${r.matched_skills.length})</h4>
            <div class="skill-tags">
              ${r.matched_skills.map((s) => `<span class="skill-tag matched">${escapeHtml(s)}</span>`).join("") || '<span style="color:var(--ink-soft); font-size:0.78rem;">None found</span>'}
            </div>
          </div>

          <div class="skills-section">
            <h4>Missing Skills (${r.missing_skills.length})</h4>
            <div class="skill-tags">
              ${r.missing_skills.map((s) => `<span class="skill-tag missing">${escapeHtml(s)}</span>`).join("") || '<span style="color:var(--ink-soft); font-size:0.78rem;">None — full skill coverage</span>'}
            </div>
          </div>
        </div>
      `;

      resultsList.appendChild(card);
    });

    resultsSection.classList.remove("hidden");
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function scoreBarRow(label, value) {
    return `
      <div class="score-bar-row">
        <span>${label}</span>
        <div class="score-bar-track"><div class="score-bar-fill" style="width:${value}%"></div></div>
        <span>${value}%</span>
      </div>`;
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str == null ? "" : String(str);
    return div.innerHTML;
  }
})();
