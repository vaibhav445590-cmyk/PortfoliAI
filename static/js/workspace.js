/**
 * PortfoliAI — Phase 6 Authenticated Workspace & Management Studio
 * Handles JWT auth, resume upload & extraction visualizer, project CRUD with
 * HTML5 drag-and-drop reordering, customization studio settings persistence,
 * and notifications.
 */

(function () {
  "use strict";

  // --- State ---
  const state = {
    token: localStorage.getItem("portfoliai_token") || null,
    user: null,
    studentId: null,
    projects: [],
    customization: {},
    profile: {}
  };

  // --- API Helpers ---
  function getAuthHeaders(isJson = true) {
    const headers = {};
    if (state.token) {
      headers["Authorization"] = `Bearer ${state.token}`;
    }
    if (isJson) {
      headers["Content-Type"] = "application/json";
    }
    return headers;
  }

  // --- Toast Notifications ---
  function showToast(message, type = "success") {
    let container = document.getElementById("toastContainer");
    if (!container) {
      container = document.createElement("div");
      container.id = "toastContainer";
      container.className = "toast-container";
      document.body.appendChild(container);
    }
    const toast = document.createElement("div");
    toast.className = `toast-message ${type}`;
    toast.innerHTML = `<span>${type === "success" ? "✓" : "⚠"}</span><span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(10px)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // --- Session & Auth Management ---
  async function initSession() {
    if (!state.token) {
      updateNavForGuest();
      return;
    }

    try {
      const resp = await fetch("/api/v1/me", {
        headers: getAuthHeaders(true)
      });

      if (resp.ok) {
        const json = await resp.json();
        if (json.success && json.data) {
          state.user = { id: json.data.user_id, email: json.data.email };
          state.studentId = json.data.student_id;
          updateNavForUser();
          loadWorkspaceData();
          return;
        }
      }
      // Invalid or expired token
      logout();
    } catch (err) {
      console.warn("Could not verify session:", err);
      updateNavForGuest();
    }
  }

  function updateNavForUser() {
    const guestNav = document.querySelectorAll(".nav-guest-only");
    const userNav = document.querySelectorAll(".nav-user-only");
    guestNav.forEach(el => el.style.display = "none");
    userNav.forEach(el => el.style.display = "flex");

    const emailDisplay = document.getElementById("userEmailDisplay");
    const avatarDisplay = document.getElementById("userAvatarInitial");
    if (emailDisplay && state.user) {
      emailDisplay.textContent = state.user.email;
    }
    if (avatarDisplay && state.user) {
      avatarDisplay.textContent = state.user.email.charAt(0).toUpperCase();
    }
  }

  function updateNavForGuest() {
    const guestNav = document.querySelectorAll(".nav-guest-only");
    const userNav = document.querySelectorAll(".nav-user-only");
    guestNav.forEach(el => el.style.display = "flex");
    userNav.forEach(el => el.style.display = "none");
  }

  function logout() {
    state.token = null;
    state.user = null;
    state.studentId = null;
    localStorage.removeItem("portfoliai_token");
    updateNavForGuest();
    showToast("Signed out successfully");
    // Switch to landing page view if inside workspace
    switchView("overview");
  }

  // --- Modal Controllers ---
  function openAuthModal(mode = "login") {
    const modal = document.getElementById("authModal");
    if (!modal) return;
    modal.classList.add("active");
    setAuthMode(mode);
  }

  function closeAuthModal() {
    const modal = document.getElementById("authModal");
    if (modal) modal.classList.remove("active");
    const alertBox = document.getElementById("authAlertBox");
    if (alertBox) alertBox.style.display = "none";
  }

  function setAuthMode(mode) {
    const tabLogin = document.getElementById("tabAuthLogin");
    const tabRegister = document.getElementById("tabAuthRegister");
    const btnSubmit = document.getElementById("btnAuthSubmit");
    const registerGroup = document.getElementById("registerConfirmGroup");

    if (mode === "register") {
      if (tabRegister) tabRegister.classList.add("active");
      if (tabLogin) tabLogin.classList.remove("active");
      if (btnSubmit) btnSubmit.textContent = "Create Account";
      if (registerGroup) registerGroup.style.display = "block";
      document.getElementById("authForm").setAttribute("data-mode", "register");
    } else {
      if (tabLogin) tabLogin.classList.add("active");
      if (tabRegister) tabRegister.classList.remove("active");
      if (btnSubmit) btnSubmit.textContent = "Sign In";
      if (registerGroup) registerGroup.style.display = "none";
      document.getElementById("authForm").setAttribute("data-mode", "login");
    }
  }

  // --- Workspace Tab Switching ---
  function switchTab(targetTabId) {
    const tabBtns = document.querySelectorAll(".workspace-tab-btn");
    const sectionViews = document.querySelectorAll(".workspace-section-view");

    tabBtns.forEach(btn => {
      if (btn.getAttribute("data-tab") === targetTabId) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    });

    sectionViews.forEach(view => {
      if (view.id === targetTabId) {
        view.classList.add("active");
      } else {
        view.classList.remove("active");
      }
    });

    if (targetTabId === "viewPreview" && window.PortfoliAIPreview) {
      window.PortfoliAIPreview.renderLivePreview();
    }
  }

  // --- Load Workspace Data ---
  async function loadWorkspaceData() {
    if (!state.token) return;

    try {
      // 1. Fetch portfolio overview & customization
      const portResp = await fetch("/api/v1/portfolio/me", {
        headers: getAuthHeaders(true)
      });
      if (portResp.ok) {
        const portData = await portResp.json();
        state.profile = portData.profile || {};
        state.customization = portData.customization || {};
        state.projects = portData.projects || [];
        renderOverviewMetrics();
        populateCustomizationControls();
        renderProjectsList();
      }

      // 2. Fetch resume metadata
      const resumeResp = await fetch("/api/v1/resume", {
        headers: getAuthHeaders(true)
      });
      if (resumeResp.ok) {
        const resumeData = await resumeResp.json();
        renderResumeMetadata(resumeData.data);
      }
    } catch (err) {
      console.error("Error loading workspace data:", err);
    }
  }

  // --- Render Overview Metrics ---
  function renderOverviewMetrics() {
    const userGreeting = document.getElementById("overviewUserGreeting");
    if (userGreeting && state.profile.name) {
      userGreeting.textContent = `Welcome back, ${state.profile.name}!`;
    }

    const publicUrlText = document.getElementById("publicPortfolioUrl");
    if (publicUrlText && state.studentId) {
      publicUrlText.textContent = `${window.location.origin}/p/${state.studentId}`;
    }

    const metricResumeStatus = document.getElementById("metricResumeStatus");
    if (metricResumeStatus) {
      metricResumeStatus.textContent = state.profile.name ? "Active" : "No Resume";
      metricResumeStatus.className = state.profile.name ? "metric-badge success" : "metric-badge draft";
    }

    const metricProjectsCount = document.getElementById("metricProjectsCount");
    if (metricProjectsCount) {
      metricProjectsCount.textContent = state.projects.length;
    }

    const metricStatusBadge = document.getElementById("metricStatusBadge");
    if (metricStatusBadge) {
      const status = state.customization.status || "draft";
      metricStatusBadge.textContent = status.toUpperCase();
      metricStatusBadge.className = status === "published" ? "metric-badge success" : "metric-badge draft";
    }

    // Completion percentage calculation
    let completion = 20; // baseline
    if (state.profile.name) completion += 25;
    if (state.profile.bio) completion += 15;
    if (state.projects.length > 0) completion += 20;
    if (state.customization.status === "published") completion += 20;

    const completionPercent = document.getElementById("overviewCompletionPercent");
    const completionFill = document.getElementById("overviewCompletionFill");
    if (completionPercent) completionPercent.textContent = `${completion}%`;
    if (completionFill) completionFill.style.width = `${completion}%`;
  }

  // --- Resume Hub & Progress Visualizer ---
  function renderResumeMetadata(metadata) {
    const factsContainer = document.getElementById("resumeFactsInspector");
    if (!factsContainer) return;

    if (!metadata || !metadata.has_resume) {
      factsContainer.innerHTML = `
        <div class="projects-empty-state">
          <div class="empty-icon">📄</div>
          <h4>No Resume Processed Yet</h4>
          <p>Drop your resume PDF to extract your experience, skills, and projects.</p>
        </div>
      `;
      return;
    }

    factsContainer.innerHTML = `
      <div class="facts-grid">
        <div class="fact-item">
          <div class="fact-label">Parsed Name & Headline</div>
          <div class="fact-content">${escapeHtml(state.profile.name || "N/A")}</div>
          <div style="font-size:0.8125rem;color:var(--text-secondary);margin-top:0.25rem;">
            ${escapeHtml(state.profile.headline || "No headline extracted")}
          </div>
        </div>
        <div class="fact-item">
          <div class="fact-label">Parsing & AI Engine</div>
          <div style="display:flex;gap:0.5rem;align-items:center;">
            <span class="skill-tag">${escapeHtml(metadata.parser_used || "pdfplumber")}</span>
            <span class="skill-tag" style="background:rgba(16,185,129,0.1);color:#059669;border-color:rgba(16,185,129,0.2);">
              ${escapeHtml(metadata.ai_provider || "Local Intelligence")}
            </span>
          </div>
        </div>
        <div class="fact-item">
          <div class="fact-label">Extracted Skills (${(state.profile.skills || []).length})</div>
          <div class="skill-chips-wrap">
            ${(state.profile.skills || []).map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join("")}
          </div>
        </div>
        <div class="fact-item">
          <div class="fact-label">Education</div>
          <div class="fact-content" style="font-size:0.875rem;">${escapeHtml(state.profile.education || "N/A")}</div>
        </div>
      </div>
    `;
  }

  async function uploadResumeFile(file) {
    if (!file) return;
    if (file.type !== "application/pdf" && !file.name.endsWith(".pdf")) {
      showToast("Please upload a valid PDF document.", "error");
      return;
    }

    const progressBox = document.getElementById("pipelineProgressBox");
    if (progressBox) progressBox.classList.add("active");

    const steps = [
      document.getElementById("pStepUpload"),
      document.getElementById("pStepExtract"),
      document.getElementById("pStepParse"),
      document.getElementById("pStepEnrich"),
      document.getElementById("pStepDone")
    ];

    function setStep(index) {
      steps.forEach((step, i) => {
        if (!step) return;
        if (i < index) {
          step.className = "pipeline-step-item done";
        } else if (i === index) {
          step.className = "pipeline-step-item current";
        } else {
          step.className = "pipeline-step-item";
        }
      });
    }

    setStep(0); // Uploading
    await new Promise(r => setTimeout(r, 400));
    setStep(1); // Extracting text

    const formData = new FormData();
    formData.append("resume", file);

    try {
      setStep(2); // Parsing & Validating
      const resp = await fetch("/upload-resume", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${state.token}`
        },
        body: formData
      });

      setStep(3); // Enriching
      await new Promise(r => setTimeout(r, 500));

      if (resp.ok) {
        setStep(4); // Done
        showToast("Resume parsed and enriched successfully!");
        await loadWorkspaceData();
        setTimeout(() => {
          if (progressBox) progressBox.classList.remove("active");
        }, 1500);
      } else {
        const errJson = await resp.json().catch(() => ({}));
        showToast(errJson.message || "Failed to process resume.", "error");
        if (progressBox) progressBox.classList.remove("active");
      }
    } catch (err) {
      console.error("Resume upload error:", err);
      showToast("An unexpected error occurred during upload.", "error");
      if (progressBox) progressBox.classList.remove("active");
    }
  }

  async function clearResume() {
    if (!confirm("Are you sure you want to clear your uploaded resume? Your custom portfolio settings will remain preserved.")) {
      return;
    }

    try {
      const resp = await fetch("/api/v1/resume", {
        method: "DELETE",
        headers: getAuthHeaders(true)
      });
      if (resp.ok) {
        showToast("Resume removed successfully.");
        await loadWorkspaceData();
      } else {
        showToast("Failed to clear resume.", "error");
      }
    } catch (err) {
      showToast("Error clearing resume.", "error");
    }
  }

  // --- Project CRUD & Drag-and-Drop Reordering ---
  function renderProjectsList() {
    const container = document.getElementById("projectsListContainer");
    if (!container) return;

    if (!state.projects || state.projects.length === 0) {
      container.innerHTML = `
        <div class="projects-empty-state">
          <div class="empty-icon">🚀</div>
          <h4>No Projects Added Yet</h4>
          <p>Projects extracted from your resume or added manually will appear here.</p>
          <button class="btn btn-primary" id="btnEmptyAddProject" style="margin-top:1rem;">
            + Add First Project
          </button>
        </div>
      `;
      const emptyBtn = document.getElementById("btnEmptyAddProject");
      if (emptyBtn) emptyBtn.addEventListener("click", () => openProjectModal());
      return;
    }

    container.innerHTML = state.projects.map((proj, idx) => `
      <div class="project-card-item" draggable="true" data-id="${proj.id}" data-index="${idx}">
        <div class="drag-handle" title="Drag to reorder">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="9" cy="5" r="1"></circle>
            <circle cx="9" cy="12" r="1"></circle>
            <circle cx="9" cy="19" r="1"></circle>
            <circle cx="15" cy="5" r="1"></circle>
            <circle cx="15" cy="12" r="1"></circle>
            <circle cx="15" cy="19" r="1"></circle>
          </svg>
        </div>
        <div class="project-card-body">
          <div class="project-card-top">
            <span class="project-card-title">${escapeHtml(proj.title)}</span>
            <span class="project-card-category">${escapeHtml(proj.category || "Project")}</span>
          </div>
          <div class="project-card-desc">${escapeHtml(proj.description || "")}</div>
          <div class="project-tech-tags">
            ${(proj.technologies || []).map(t => `<span class="tech-tag">${escapeHtml(t)}</span>`).join("")}
          </div>
          <div class="project-links">
            ${proj.github_url ? `<a href="${escapeHtml(proj.github_url)}" target="_blank" rel="noopener" class="project-link-item">GitHub ↗</a>` : ""}
            ${proj.live_url ? `<a href="${escapeHtml(proj.live_url)}" target="_blank" rel="noopener" class="project-link-item">Live Demo ↗</a>` : ""}
          </div>
        </div>
        <div class="project-card-actions">
          <button class="btn btn-outline btn-edit-proj" data-id="${proj.id}" style="padding:0.4rem 0.75rem;font-size:0.8125rem;">Edit</button>
          <button class="btn btn-outline btn-delete-proj" data-id="${proj.id}" style="padding:0.4rem 0.75rem;font-size:0.8125rem;color:#e11d48;">Delete</button>
        </div>
      </div>
    `).join("");

    attachProjectEvents();
  }

  function attachProjectEvents() {
    // Edit & Delete Buttons
    document.querySelectorAll(".btn-edit-proj").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.getAttribute("data-id"), 10);
        const proj = state.projects.find(p => p.id === id);
        if (proj) openProjectModal(proj);
      });
    });

    document.querySelectorAll(".btn-delete-proj").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.getAttribute("data-id"), 10);
        deleteProject(id);
      });
    });

    // HTML5 Drag and Drop Reordering
    const cards = document.querySelectorAll(".project-card-item");
    let draggedItem = null;

    cards.forEach(card => {
      card.addEventListener("dragstart", (e) => {
        draggedItem = card;
        card.classList.add("dragging");
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/plain", card.getAttribute("data-id"));
      });

      card.addEventListener("dragend", () => {
        card.classList.remove("dragging");
        cards.forEach(c => c.classList.remove("drag-over-top", "drag-over-bottom"));
        draggedItem = null;
      });

      card.addEventListener("dragover", (e) => {
        e.preventDefault();
        if (card === draggedItem) return;
        const rect = card.getBoundingClientRect();
        const midY = rect.top + rect.height / 2;
        if (e.clientY < midY) {
          card.classList.add("drag-over-top");
          card.classList.remove("drag-over-bottom");
        } else {
          card.classList.add("drag-over-bottom");
          card.classList.remove("drag-over-top");
        }
      });

      card.addEventListener("dragleave", () => {
        card.classList.remove("drag-over-top", "drag-over-bottom");
      });

      card.addEventListener("drop", async (e) => {
        e.preventDefault();
        card.classList.remove("drag-over-top", "drag-over-bottom");
        if (!draggedItem || draggedItem === card) return;

        const container = document.getElementById("projectsListContainer");
        const rect = card.getBoundingClientRect();
        const midY = rect.top + rect.height / 2;

        if (e.clientY < midY) {
          container.insertBefore(draggedItem, card);
        } else {
          container.insertBefore(draggedItem, card.nextSibling);
        }

        // Gather new order of project IDs
        const newOrder = Array.from(container.querySelectorAll(".project-card-item"))
          .map(el => parseInt(el.getAttribute("data-id"), 10));

        // Persist order to backend via PUT /api/v1/portfolio
        await persistProjectOrder(newOrder);
      });
    });
  }

  async function persistProjectOrder(orderedIds) {
    try {
      const resp = await fetch("/api/v1/portfolio", {
        method: "PUT",
        headers: getAuthHeaders(true),
        body: JSON.stringify({ project_order: orderedIds })
      });
      if (resp.ok) {
        showToast("Project order updated and saved.");
        // Update local state order
        const map = new Map(state.projects.map(p => [p.id, p]));
        state.projects = orderedIds.map(id => map.get(id)).filter(Boolean);
        if (window.PortfoliAIPreview) {
          window.PortfoliAIPreview.renderLivePreview();
        }
      }
    } catch (err) {
      console.error("Failed to save project order:", err);
    }
  }

  function openProjectModal(proj = null) {
    const modal = document.getElementById("projectModal");
    if (!modal) return;

    document.getElementById("projModalTitle").textContent = proj ? "Edit Project" : "Add Project";
    document.getElementById("projIdInput").value = proj ? proj.id : "";
    document.getElementById("projTitleInput").value = proj ? proj.title : "";
    document.getElementById("projCategoryInput").value = proj ? (proj.category || "Web Development") : "Web Development";
    document.getElementById("projDescInput").value = proj ? proj.description : "";
    document.getElementById("projTechInput").value = proj ? (proj.technologies || []).join(", ") : "";
    document.getElementById("projGithubInput").value = proj ? (proj.github_url || "") : "";
    document.getElementById("projLiveInput").value = proj ? (proj.live_url || "") : "";

    modal.classList.add("active");
  }

  function closeProjectModal() {
    const modal = document.getElementById("projectModal");
    if (modal) modal.classList.remove("active");
  }

  async function saveProjectForm(e) {
    e.preventDefault();
    const projId = document.getElementById("projIdInput").value;
    const title = document.getElementById("projTitleInput").value.trim();
    const category = document.getElementById("projCategoryInput").value;
    const description = document.getElementById("projDescInput").value.trim();
    const techRaw = document.getElementById("projTechInput").value;
    const githubUrl = document.getElementById("projGithubInput").value.trim();
    const liveUrl = document.getElementById("projLiveInput").value.trim();

    if (!title) {
      showToast("Project title is required.", "error");
      return;
    }

    const technologies = techRaw
      .split(",")
      .map(t => t.trim())
      .filter(Boolean);

    const payload = {
      title,
      category,
      description,
      technologies,
      github_url: githubUrl || null,
      live_url: liveUrl || null
    };

    try {
      const url = projId ? `/api/v1/projects/${projId}` : "/api/v1/projects";
      const method = projId ? "PUT" : "POST";

      const resp = await fetch(url, {
        method,
        headers: getAuthHeaders(true),
        body: JSON.stringify(payload)
      });

      if (resp.ok) {
        showToast(projId ? "Project updated successfully!" : "Project created successfully!");
        closeProjectModal();
        await loadWorkspaceData();
        if (window.PortfoliAIPreview) {
          window.PortfoliAIPreview.renderLivePreview();
        }
      } else {
        const err = await resp.json().catch(() => ({}));
        showToast(err.error?.message || "Failed to save project.", "error");
      }
    } catch (err) {
      showToast("Error saving project.", "error");
    }
  }

  async function deleteProject(id) {
    if (!confirm("Are you sure you want to delete this project?")) return;

    try {
      const resp = await fetch(`/api/v1/projects/${id}`, {
        method: "DELETE",
        headers: getAuthHeaders(true)
      });
      if (resp.ok) {
        showToast("Project deleted.");
        await loadWorkspaceData();
        if (window.PortfoliAIPreview) {
          window.PortfoliAIPreview.renderLivePreview();
        }
      } else {
        showToast("Failed to delete project.", "error");
      }
    } catch (err) {
      showToast("Error deleting project.", "error");
    }
  }

  // --- Customization Studio Settings Binder ---
  function populateCustomizationControls() {
    const cust = state.customization || {};

    // 1. Template
    document.querySelectorAll(".template-choice-card").forEach(card => {
      if (card.getAttribute("data-template") === (cust.template || "glass")) {
        card.classList.add("active");
      } else {
        card.classList.remove("active");
      }
    });

    // 2. Theme
    document.querySelectorAll(".theme-pill-btn").forEach(btn => {
      if (btn.getAttribute("data-theme") === (cust.theme || "glass")) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    });

    // 3. Accent
    document.querySelectorAll(".accent-swatch-btn").forEach(btn => {
      if (btn.getAttribute("data-accent") === (cust.accent || "purple")) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    });

    // 4. Section Visibility
    const secVis = cust.section_visibility || {
      about: true, skills: true, education: true, experience: true, projects: true, achievements: true
    };
    for (const [sec, isVis] of Object.entries(secVis)) {
      const chk = document.getElementById(`toggleSec_${sec}`);
      if (chk) chk.checked = !!isVis;
    }

    // 5. Custom text fields
    const nameInput = document.getElementById("custCustomName");
    const headlineInput = document.getElementById("custCustomHeadline");
    const bioInput = document.getElementById("custCustomBio");
    if (nameInput) nameInput.value = cust.custom_name || "";
    if (headlineInput) headlineInput.value = cust.custom_headline || "";
    if (bioInput) bioInput.value = cust.custom_bio || "";

    // 6. Social links
    const socials = cust.social_links || {};
    const githubLink = document.getElementById("custSocialGithub");
    const linkedinLink = document.getElementById("custSocialLinkedin");
    const twitterLink = document.getElementById("custSocialTwitter");
    if (githubLink) githubLink.value = socials.github || "";
    if (linkedinLink) linkedinLink.value = socials.linkedin || "";
    if (twitterLink) twitterLink.value = socials.twitter || "";

    // 7. Status
    const statusRadioPub = document.getElementById("statusPublished");
    const statusRadioDraft = document.getElementById("statusDraft");
    if (cust.status === "published") {
      if (statusRadioPub) statusRadioPub.checked = true;
    } else {
      if (statusRadioDraft) statusRadioDraft.checked = true;
    }
  }

  async function saveCustomizationSettings() {
    const payload = {};

    // Template
    const activeTemplate = document.querySelector(".template-choice-card.active");
    if (activeTemplate) payload.template = activeTemplate.getAttribute("data-template");

    // Theme
    const activeTheme = document.querySelector(".theme-pill-btn.active");
    if (activeTheme) payload.theme = activeTheme.getAttribute("data-theme");

    // Accent
    const activeAccent = document.querySelector(".accent-swatch-btn.active");
    if (activeAccent) payload.accent = activeAccent.getAttribute("data-accent");

    // Section visibility
    const sections = ["about", "skills", "education", "experience", "projects", "achievements"];
    const secVis = {};
    sections.forEach(s => {
      const chk = document.getElementById(`toggleSec_${s}`);
      if (chk) secVis[s] = chk.checked;
    });
    payload.section_visibility = secVis;

    // Custom text overrides
    const nameInput = document.getElementById("custCustomName");
    const headlineInput = document.getElementById("custCustomHeadline");
    const bioInput = document.getElementById("custCustomBio");
    payload.custom_name = nameInput ? nameInput.value.trim() : "";
    payload.custom_headline = headlineInput ? headlineInput.value.trim() : "";
    payload.custom_bio = bioInput ? bioInput.value.trim() : "";

    // Social Links
    const githubLink = document.getElementById("custSocialGithub");
    const linkedinLink = document.getElementById("custSocialLinkedin");
    const twitterLink = document.getElementById("custSocialTwitter");
    payload.social_links = {
      github: githubLink ? githubLink.value.trim() : "",
      linkedin: linkedinLink ? linkedinLink.value.trim() : "",
      twitter: twitterLink ? twitterLink.value.trim() : ""
    };

    // Status
    const statusPub = document.getElementById("statusPublished");
    payload.status = (statusPub && statusPub.checked) ? "published" : "draft";

    try {
      const resp = await fetch("/api/v1/portfolio", {
        method: "PUT",
        headers: getAuthHeaders(true),
        body: JSON.stringify(payload)
      });

      if (resp.ok) {
        showToast("Portfolio customization saved successfully!");
        await loadWorkspaceData();
        if (window.PortfoliAIPreview) {
          window.PortfoliAIPreview.renderLivePreview();
        }
      } else {
        const err = await resp.json().catch(() => ({}));
        showToast(err.error?.message || "Failed to update settings.", "error");
      }
    } catch (err) {
      showToast("Error updating settings.", "error");
    }
  }

  // --- Copy Public Link Helper ---
  function copyPublicLink() {
    if (!state.studentId) {
      showToast("No active portfolio student profile found.", "error");
      return;
    }
    const url = `${window.location.origin}/p/${state.studentId}`;
    navigator.clipboard.writeText(url).then(() => {
      showToast("Public portfolio link copied to clipboard!");
    }).catch(() => {
      showToast("Could not copy link to clipboard.", "error");
    });
  }

  // --- Initialize Event Listeners on DOMContentLoaded ---
  document.addEventListener("DOMContentLoaded", () => {
    initSession();

    // Workspace Navigation Tabs
    document.querySelectorAll(".workspace-tab-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const target = btn.getAttribute("data-tab");
        switchTab(target);
      });
    });

    // Auth Buttons & Triggers
    document.querySelectorAll(".btn-open-login").forEach(btn => {
      btn.addEventListener("click", () => openAuthModal("login"));
    });
    document.querySelectorAll(".btn-open-register").forEach(btn => {
      btn.addEventListener("click", () => openAuthModal("register"));
    });
    document.querySelectorAll(".modal-close-btn").forEach(btn => {
      btn.addEventListener("click", closeAuthModal);
    });

    const tabAuthLogin = document.getElementById("tabAuthLogin");
    const tabAuthRegister = document.getElementById("tabAuthRegister");
    if (tabAuthLogin) tabAuthLogin.addEventListener("click", () => setAuthMode("login"));
    if (tabAuthRegister) tabAuthRegister.addEventListener("click", () => setAuthMode("register"));

    // Auth Form Submission
    const authForm = document.getElementById("authForm");
    if (authForm) {
      authForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const mode = authForm.getAttribute("data-mode") || "login";
        const email = document.getElementById("authEmail").value.trim();
        const password = document.getElementById("authPassword").value;
        const confirmPassword = document.getElementById("authConfirmPassword")?.value;
        const alertBox = document.getElementById("authAlertBox");

        if (mode === "register" && password !== confirmPassword) {
          alertBox.textContent = "Passwords do not match.";
          alertBox.className = "auth-alert-box error";
          return;
        }

        const endpoint = mode === "register" ? "/api/v1/auth/register" : "/api/v1/auth/login";
        try {
          const resp = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
          });
          const json = await resp.json();

          if (resp.ok && json.success) {
            state.token = json.data.token;
            localStorage.setItem("portfoliai_token", state.token);
            closeAuthModal();
            showToast(mode === "register" ? "Account created! Welcome to PortfoliAI." : "Signed in successfully!");
            initSession();
          } else {
            alertBox.textContent = json.error?.message || json.message || "Authentication failed.";
            alertBox.className = "auth-alert-box error";
          }
        } catch (err) {
          alertBox.textContent = "Network error. Please try again.";
          alertBox.className = "auth-alert-box error";
        }
      });
    }

    // Sign Out Button
    const btnSignOut = document.getElementById("btnSignOut");
    if (btnSignOut) btnSignOut.addEventListener("click", logout);

    // Resume Dropzone & File Input
    const dropzone = document.getElementById("resumeDropzone");
    const fileInput = document.getElementById("resumeFileInput");
    if (dropzone && fileInput) {
      dropzone.addEventListener("click", () => fileInput.click());
      dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
      });
      dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("dragover");
      });
      dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
          uploadResumeFile(e.dataTransfer.files[0]);
        }
      });
      fileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files.length > 0) {
          uploadResumeFile(e.target.files[0]);
        }
      });
    }

    // Resume Clear Action
    const btnClearResume = document.getElementById("btnClearResume");
    if (btnClearResume) btnClearResume.addEventListener("click", clearResume);

    // Project Modal & Form
    const btnAddProject = document.getElementById("btnAddProject");
    if (btnAddProject) btnAddProject.addEventListener("click", () => openProjectModal());

    const btnCloseProjModal = document.getElementById("btnCloseProjModal");
    if (btnCloseProjModal) btnCloseProjModal.addEventListener("click", closeProjectModal);

    const projForm = document.getElementById("projectForm");
    if (projForm) projForm.addEventListener("submit", saveProjectForm);

    // Customization Studio Card Selectors
    document.querySelectorAll(".template-choice-card").forEach(card => {
      card.addEventListener("click", () => {
        document.querySelectorAll(".template-choice-card").forEach(c => c.classList.remove("active"));
        card.classList.add("active");
        if (window.PortfoliAIPreview) window.PortfoliAIPreview.updatePreviewStyles();
      });
    });

    document.querySelectorAll(".theme-pill-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".theme-pill-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        if (window.PortfoliAIPreview) window.PortfoliAIPreview.updatePreviewStyles();
      });
    });

    document.querySelectorAll(".accent-swatch-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".accent-swatch-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        if (window.PortfoliAIPreview) window.PortfoliAIPreview.updatePreviewStyles();
      });
    });

    const btnSaveCustomization = document.getElementById("btnSaveCustomization");
    if (btnSaveCustomization) btnSaveCustomization.addEventListener("click", saveCustomizationSettings);

    // Public Link Copy Buttons
    document.querySelectorAll(".btn-copy-public-link").forEach(btn => {
      btn.addEventListener("click", copyPublicLink);
    });
  });

  // Export State and methods for Live Preview
  window.PortfoliAIWorkspace = {
    state,
    getAuthHeaders,
    loadWorkspaceData,
    switchTab,
    showToast
  };

})();
