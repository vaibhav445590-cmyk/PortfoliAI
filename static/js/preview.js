/**
 * PortfoliAI — Phase 6 Live Portfolio Preview Engine
 * Fetches real user portfolio data via /api/v1/portfolio/me/preview,
 * supports real-time reactive DOM syncing with Customization Studio controls,
 * and handles Desktop / Tablet / Mobile responsive device framing.
 */

(function () {
  "use strict";

  let previewData = null;

  async function fetchPreviewData() {
    if (!window.PortfoliAIWorkspace || !window.PortfoliAIWorkspace.state.token) {
      return null;
    }

    try {
      const resp = await fetch("/api/v1/portfolio/me/preview", {
        headers: window.PortfoliAIWorkspace.getAuthHeaders(true)
      });
      if (resp.ok) {
        const json = await resp.json();
        previewData = json;
        return json;
      }
    } catch (err) {
      console.warn("Could not fetch preview data:", err);
    }
    return null;
  }

  function getActiveStudioControls() {
    const templateEl = document.querySelector(".template-choice-card.active");
    const themeEl = document.querySelector(".theme-pill-btn.active");
    const accentEl = document.querySelector(".accent-swatch-btn.active");

    const template = templateEl ? templateEl.getAttribute("data-template") : "glass";
    const theme = themeEl ? themeEl.getAttribute("data-theme") : "glass";
    const accent = accentEl ? accentEl.getAttribute("data-accent") : "purple";

    const customName = document.getElementById("custCustomName")?.value.trim();
    const customHeadline = document.getElementById("custCustomHeadline")?.value.trim();
    const customBio = document.getElementById("custCustomBio")?.value.trim();

    const sections = ["about", "skills", "education", "experience", "projects", "achievements"];
    const visibility = {};
    sections.forEach(s => {
      const chk = document.getElementById(`toggleSec_${s}`);
      visibility[s] = chk ? chk.checked : true;
    });

    const socialLinks = {
      github: document.getElementById("custSocialGithub")?.value.trim() || "",
      linkedin: document.getElementById("custSocialLinkedin")?.value.trim() || "",
      twitter: document.getElementById("custSocialTwitter")?.value.trim() || ""
    };

    return {
      template,
      theme,
      accent,
      customName,
      customHeadline,
      customBio,
      visibility,
      socialLinks
    };
  }

  async function renderLivePreview() {
    const container = document.getElementById("previewFrameInner");
    if (!container) return;

    let data = previewData;
    if (!data) {
      data = await fetchPreviewData();
    }

    const controls = getActiveStudioControls();

    // Fallback if user has no resume/profile yet
    const profile = data?.profile || {
      name: controls.customName || "Student Portfolio",
      headline: controls.customHeadline || "Software Engineer",
      bio: controls.customBio || "Engineering student building intelligent systems and software solutions.",
      skills: [],
      education: "",
      experience: "",
      achievements: ""
    };

    // Overlay real-time inputs
    const displayName = controls.customName || profile.name || "Student Portfolio";
    const displayHeadline = controls.customHeadline || profile.headline || "Software Engineer";
    const displayBio = controls.customBio || profile.bio || "Engineering student building intelligent systems and software solutions.";
    const projects = (data?.projects && data.projects.length > 0)
      ? data.projects
      : ((window.PortfoliAIWorkspace?.state.projects && window.PortfoliAIWorkspace.state.projects.length > 0)
          ? window.PortfoliAIWorkspace.state.projects
          : []);

    const templateClass = `template-${controls.template}`;
    const themeClass = `theme-${controls.theme}`;
    const accentClass = `accent-${controls.accent}`;

    // Generate HTML based on selected template archetype
    let html = `
      <div class="portfolio-root ${templateClass} ${themeClass} ${accentClass}">
        <div class="portfolio-container">
    `;

    // Template-specific Hero
    if (controls.template === "minimal") {
      html += `
        <header class="minimal-hero">
          <h1 class="minimal-name">${escapeHtml(displayName)}</h1>
          ${displayHeadline ? `<div class="minimal-headline">${escapeHtml(displayHeadline)}</div>` : ""}
          ${displayBio && controls.visibility.about ? `<p class="minimal-bio">${escapeHtml(displayBio)}</p>` : ""}
          ${renderSocialLinks(controls.socialLinks)}
        </header>
      `;
    } else if (controls.template === "modern") {
      html += `
        <header class="modern-hero">
          <div>
            <span class="modern-tag">AVAILABLE FOR OPPORTUNITIES</span>
            <h1 class="modern-name">${escapeHtml(displayName)}</h1>
            ${displayHeadline ? `<div style="font-size:1.25rem;color:var(--portfolio-accent);font-weight:600;margin-bottom:1rem;">${escapeHtml(displayHeadline)}</div>` : ""}
            ${displayBio && controls.visibility.about ? `<p style="font-size:1.0625rem;color:var(--text-secondary);line-height:1.7;">${escapeHtml(displayBio)}</p>` : ""}
            ${renderSocialLinks(controls.socialLinks)}
          </div>
          <div style="background:var(--portfolio-card-bg);border:1px solid var(--portfolio-border);border-radius:var(--radius-2xl);padding:1.75rem;text-align:center;">
            <div style="width:72px;height:72px;border-radius:50%;background:var(--portfolio-accent);color:#fff;font-size:1.75rem;font-weight:800;display:flex;align-items:center;justify-content:center;margin:0 auto 1rem;">
              ${displayName.charAt(0).toUpperCase()}
            </div>
            <div style="font-weight:700;font-size:1.125rem;">Verified Portfolio</div>
            <div style="font-size:0.8125rem;color:var(--portfolio-text-muted,#64748b);margin-top:0.25rem;">PortfoliAI Phase 6</div>
          </div>
        </header>
      `;
    } else if (controls.template === "developer") {
      html += `
        <div class="terminal-window" style="margin-bottom:3rem;">
          <div class="terminal-titlebar">
            <div class="terminal-dots">
              <span class="terminal-dot dot-red"></span>
              <span class="terminal-dot dot-yellow"></span>
              <span class="terminal-dot dot-green"></span>
            </div>
            <span style="font-size:0.75rem;color:#94a3b8;">developer@portfoliai:~</span>
          </div>
          <div class="terminal-body">
            <div class="cli-prompt"><span class="path">~/portfolio</span> <span class="branch">(main)</span> $ whoami</div>
            <h1 class="dev-name">${escapeHtml(displayName)}</h1>
            <div style="color:#a855f7;font-size:1rem;margin-bottom:1rem;">// ${escapeHtml(displayHeadline)}</div>
            ${displayBio && controls.visibility.about ? `
              <div class="dev-code-block">
                const profile = {<br>
                &nbsp;&nbsp;name: "${escapeHtml(displayName)}",<br>
                &nbsp;&nbsp;bio: "${escapeHtml(displayBio)}"<br>
                };
              </div>
            ` : ""}
            ${renderSocialLinks(controls.socialLinks)}
          </div>
        </div>
      `;
    } else if (controls.template === "dark") {
      html += `
        <header class="dark-hero">
          <div class="dark-glow-orb"></div>
          <h1 class="dark-name">${escapeHtml(displayName)}</h1>
          ${displayHeadline ? `<div style="font-size:1.25rem;color:var(--portfolio-accent);font-weight:600;margin-bottom:1rem;">${escapeHtml(displayHeadline)}</div>` : ""}
          ${displayBio && controls.visibility.about ? `<p style="max-width:650px;margin:0 auto 1.5rem;font-size:1.0625rem;color:#94a3b8;line-height:1.7;">${escapeHtml(displayBio)}</p>` : ""}
          ${renderSocialLinks(controls.socialLinks)}
        </header>
      `;
    } else {
      // Default: Glass
      html += `
        <header class="glass-hero">
          <div class="glass-avatar-ring">${displayName.charAt(0).toUpperCase()}</div>
          <h1 class="glass-name">${escapeHtml(displayName)}</h1>
          ${displayHeadline ? `<div class="glass-headline">${escapeHtml(displayHeadline)}</div>` : ""}
          ${displayBio && controls.visibility.about ? `<p class="glass-bio">${escapeHtml(displayBio)}</p>` : ""}
          ${renderSocialLinks(controls.socialLinks)}
        </header>
      `;
    }

    // Projects Section
    if (controls.visibility.projects && projects.length > 0) {
      html += `
        <section class="portfolio-section">
          <h2 class="portfolio-section-title">
            <span class="accent-color-text">/</span> Featured Projects
          </h2>
          <div class="portfolio-projects-grid">
            ${projects.map(p => `
              <div class="glass-card">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.5rem;">
                  <h3 style="font-size:1.125rem;font-weight:700;">${escapeHtml(p.title)}</h3>
                  <span style="font-size:0.6875rem;padding:0.15rem 0.5rem;border-radius:var(--radius-full);background:var(--portfolio-accent-subtle);color:var(--portfolio-accent);font-weight:700;">${escapeHtml(p.category || "Project")}</span>
                </div>
                <p style="font-size:0.875rem;color:var(--portfolio-text-muted,#475569);line-height:1.5;margin-bottom:1rem;">
                  ${escapeHtml(p.description || "")}
                </p>
                <div style="display:flex;flex-wrap:wrap;gap:0.35rem;margin-bottom:1rem;">
                  ${(p.technologies || []).map(t => `<span class="portfolio-skill-pill">${escapeHtml(t)}</span>`).join("")}
                </div>
                <div style="display:flex;gap:1rem;font-size:0.8125rem;">
                  ${p.github_url ? `<a href="${escapeHtml(p.github_url)}" target="_blank" rel="noopener" class="accent-color-text" style="font-weight:600;text-decoration:none;">GitHub ↗</a>` : ""}
                  ${p.live_url ? `<a href="${escapeHtml(p.live_url)}" target="_blank" rel="noopener" class="accent-color-text" style="font-weight:600;text-decoration:none;">Live Demo ↗</a>` : ""}
                </div>
              </div>
            `).join("")}
          </div>
        </section>
      `;
    }

    // Skills Section
    if (controls.visibility.skills && (profile.skills || []).length > 0) {
      html += `
        <section class="portfolio-section">
          <h2 class="portfolio-section-title">
            <span class="accent-color-text">/</span> Core Technologies
          </h2>
          <div class="portfolio-skills-chips">
            ${(profile.skills || []).map(s => `
              <span class="portfolio-skill-pill">${escapeHtml(s)}</span>
            `).join("")}
          </div>
        </section>
      `;
    }

    // Experience Section
    if (controls.visibility.experience && profile.experience) {
      html += `
        <section class="portfolio-section">
          <h2 class="portfolio-section-title">
            <span class="accent-color-text">/</span> Experience
          </h2>
          <div class="glass-card">
            <p style="font-size:0.9375rem;color:var(--text-secondary);">${escapeHtml(profile.experience)}</p>
          </div>
        </section>
      `;
    }

    // Education Section
    if (controls.visibility.education && profile.education) {
      html += `
        <section class="portfolio-section">
          <h2 class="portfolio-section-title">
            <span class="accent-color-text">/</span> Education
          </h2>
          <div class="glass-card">
            <p style="font-size:0.9375rem;color:var(--text-secondary);">${escapeHtml(profile.education)}</p>
          </div>
        </section>
      `;
    }

    // Achievements Section
    if (controls.visibility.achievements && profile.achievements) {
      html += `
        <section class="portfolio-section">
          <h2 class="portfolio-section-title">
            <span class="accent-color-text">/</span> Honors & Achievements
          </h2>
          <div class="glass-card">
            <p style="font-size:0.9375rem;color:var(--text-secondary);">${escapeHtml(profile.achievements)}</p>
          </div>
        </section>
      `;
    }

    html += `
        </div>
      </div>
    `;

    container.innerHTML = html;
  }

  function renderSocialLinks(socials = {}) {
    const items = [];
    if (socials.github) {
      items.push(`<a href="${escapeHtml(socials.github)}" target="_blank" rel="noopener" class="portfolio-social-btn">GitHub ↗</a>`);
    }
    if (socials.linkedin) {
      items.push(`<a href="${escapeHtml(socials.linkedin)}" target="_blank" rel="noopener" class="portfolio-social-btn">LinkedIn ↗</a>`);
    }
    if (socials.twitter) {
      items.push(`<a href="${escapeHtml(socials.twitter)}" target="_blank" rel="noopener" class="portfolio-social-btn">Twitter/X ↗</a>`);
    }
    if (items.length === 0) return "";
    return `<div class="portfolio-social-nav" style="justify-content:center;">${items.join("")}</div>`;
  }

  function updatePreviewStyles() {
    renderLivePreview();
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

  // --- Device Switcher Initialization ---
  document.addEventListener("DOMContentLoaded", () => {
    const frame = document.getElementById("previewFrameWrapper");
    const btns = document.querySelectorAll(".device-btn");

    btns.forEach(btn => {
      btn.addEventListener("click", () => {
        btns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        const device = btn.getAttribute("data-device");
        if (frame) {
          frame.className = "preview-frame " + (device === "desktop" ? "" : device);
        }
      });
    });

    // Real-time keystroke listeners in Customization Studio
    ["custCustomName", "custCustomHeadline", "custCustomBio"].forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener("input", () => {
          renderLivePreview();
        });
      }
    });

    // Section visibility checkbox change listeners
    ["about", "skills", "education", "experience", "projects", "achievements"].forEach(sec => {
      const chk = document.getElementById(`toggleSec_${sec}`);
      if (chk) {
        chk.addEventListener("change", () => {
          renderLivePreview();
        });
      }
    });
  });

  // Export for global access
  window.PortfoliAIPreview = {
    renderLivePreview,
    updatePreviewStyles,
    fetchPreviewData
  };

})();
