/**
 * PortfoliAI — Phase 6.1 Cinematic Motion System
 * Unified scroll-driven animation engine with:
 *   - Hero resume scroll parallax & progressive extraction highlights
 *   - Sticky pipeline storytelling with stage activation & progress track
 *   - Template showcase cinematic crossfade
 *   - Bento card stagger reveal via IntersectionObserver
 *   - Cursor glow tracking (rAF)
 *   - Scroll progress bar
 *   - prefers-reduced-motion respect
 *   - Mobile motion reduction
 */

(function () {
  "use strict";

  // --- Feature Detection & Preferences ---
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const isMobile = window.innerWidth <= 768;
  const isDesktopPointer = window.matchMedia("(pointer: fine)").matches;

  // ==========================================================================
  // 1. SCROLL PROGRESS BAR & 2. AMBIENT CURSOR LIGHT TRACKING
  // ==========================================================================
  const scrollBar = document.getElementById("scrollProgressBar");
  const cursorGlow = document.getElementById("cursorGlow");
  const motionEngine = window.PortfoliAIMotion;

  if (motionEngine) {
    // Coordinated via Master Motion Engine (Single RAF loop)
    let curX = 0, curY = 0;
    motionEngine.registerScene("phase6-chrome", {
      runAlways: true,
      onTick: ({ scroll, pointer }) => {
        if (scrollBar && !prefersReducedMotion) {
          scrollBar.style.width = (scroll.progress * 100).toFixed(1) + "%";
        }
        if (cursorGlow && isDesktopPointer && !prefersReducedMotion && pointer.isInside) {
          curX += (pointer.clientX - curX) * 0.12;
          curY += (pointer.clientY - curY) * 0.12;
          cursorGlow.style.transform = `translate3d(${curX - 250}px, ${curY - 250}px, 0)`;
        }
      }
    });
  } else {
    // Standalone fallback if Motion Engine is not loaded
    if (scrollBar && !prefersReducedMotion) {
      window.addEventListener("scroll", () => {
        const winScroll = document.documentElement.scrollTop || document.body.scrollTop;
        const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        const scrolled = height > 0 ? (winScroll / height) * 100 : 0;
        scrollBar.style.width = scrolled + "%";
      }, { passive: true });
    }

    if (cursorGlow && isDesktopPointer && !prefersReducedMotion) {
      let mouseX = 0, mouseY = 0;
      let currentX = 0, currentY = 0;

      window.addEventListener("mousemove", (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
      }, { passive: true });

      function renderCursor() {
        currentX += (mouseX - currentX) * 0.12;
        currentY += (mouseY - currentY) * 0.12;
        cursorGlow.style.transform = `translate3d(${currentX - 250}px, ${currentY - 250}px, 0)`;
        requestAnimationFrame(renderCursor);
      }
      requestAnimationFrame(renderCursor);
    }
  }

  // ==========================================================================
  // 3. 3D FLOATING RESUME — Mouse Hover Tilt & Parallax
  // ==========================================================================
  const resumeCard = document.getElementById("hero3DResume");
  const heroSection = document.querySelector(".hero-section");
  const heroContent = document.querySelector(".hero-content");
  let isMouseHovering = false;

  const isPhase7Immersive = !!document.getElementById("immersiveNarrative");

  if (resumeCard && !prefersReducedMotion && !isMobile && !isPhase7Immersive) {
    const parentContainer = resumeCard.closest(".hero-perspective-scene") || resumeCard.parentElement;

    parentContainer.addEventListener("mouseenter", () => {
      isMouseHovering = true;
      resumeCard.style.transition = "transform 0.1s ease-out, box-shadow 0.3s ease";
    });

    parentContainer.addEventListener("mousemove", (e) => {
      if (!isMouseHovering) return;
      const rect = parentContainer.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const rotateX = ((y - centerY) / centerY) * -14;
      const rotateY = ((x - centerX) / centerX) * 14;
      resumeCard.style.transform = `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) scale3d(1.03, 1.03, 1.03)`;
    });

    parentContainer.addEventListener("mouseleave", () => {
      isMouseHovering = false;
      resumeCard.style.transition = "transform 0.7s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.7s ease";
      updateHeroParallax();
    });
  }

  // ==========================================================================
  // 4. HERO SCROLL-DRIVEN PARALLAX (Unified in master rAF loop)
  // ==========================================================================
  const resumePills = document.querySelectorAll(".resume-pill");
  const resumeHighlight = document.querySelector(".resume-doc-card");
  const resumeAiBadge = document.querySelector(".resume-ai-badge");

  function updateHeroParallax() {
    if (!heroSection || prefersReducedMotion || isMobile) return;

    const rect = heroSection.getBoundingClientRect();
    const sectionHeight = heroSection.offsetHeight;
    // Normalized scroll progress through hero: 0 (at top) to 1 (scrolled past hero)
    const progress = Math.max(0, Math.min(1, -rect.top / (sectionHeight * 0.75)));

    // Subtle 3D perspective shift on the resume card (when not hovered)
    if (resumeCard && !isMouseHovering) {
      const rotX = 4 + progress * 7;      // 4deg -> 11deg
      const rotY = -8 + progress * 5;     // -8deg -> -3deg
      const scaleVal = 1 - progress * 0.03; // 1.0 -> 0.97
      const translateY = progress * -20;  // 0 -> -20px
      resumeCard.style.transform =
        `perspective(1000px) rotateX(${rotX.toFixed(2)}deg) rotateY(${rotY.toFixed(2)}deg) scale3d(${scaleVal}, ${scaleVal}, 1) translateY(${translateY.toFixed(1)}px)`;
    }

    // Gentle fade & drift on hero text
    if (heroContent) {
      const fadeVal = 1 - progress * 0.45;
      const driftY = progress * 16;
      heroContent.style.opacity = Math.max(0, fadeVal).toFixed(3);
      heroContent.style.transform = `translateY(${driftY.toFixed(1)}px)`;
    }

    // Storytelling extraction highlights: chips shimmer when scrolled
    if (progress > 0.15) {
      resumePills.forEach((p, idx) => {
        if (progress > 0.15 + idx * 0.05) {
          p.classList.add("scrolled-active");
        } else {
          p.classList.remove("scrolled-active");
        }
      });
    } else {
      resumePills.forEach(p => p.classList.remove("scrolled-active"));
    }

    // Verified highlight card border glow
    if (resumeHighlight) {
      if (progress > 0.35) {
        resumeHighlight.classList.add("scrolled-active");
      } else {
        resumeHighlight.classList.remove("scrolled-active");
      }
    }

    // AI badge glow
    if (resumeAiBadge) {
      if (progress > 0.45) {
        resumeAiBadge.classList.add("scrolled-active");
      } else {
        resumeAiBadge.classList.remove("scrolled-active");
      }
    }
  }

  // ==========================================================================
  // 5. TRANSFORMATION PIPELINE — Sticky Scroll Storytelling
  // ==========================================================================
  const pipelineRunway = document.querySelector(".pipeline-scroll-runway");
  const pipelineContainer = document.querySelector(".story-container-sticky");
  const pipelineProgressBar = document.querySelector(".pipeline-progress-bar");
  const storySteps = document.querySelectorAll(".story-step-item");

  function setStage(activeIndex) {
    storySteps.forEach((step, i) => {
      step.classList.remove("stage-active", "stage-past", "stage-future", "active");
      if (i < activeIndex) {
        step.classList.add("stage-past");
      } else if (i === activeIndex) {
        step.classList.add("stage-active", "active");
      } else {
        step.classList.add("stage-future");
      }
    });
  }

  function updatePipelineProgress() {
    if (!pipelineRunway || storySteps.length === 0 || prefersReducedMotion || isMobile) return;

    const rect = pipelineRunway.getBoundingClientRect();
    const runwayHeight = pipelineRunway.offsetHeight;
    const containerHeight = pipelineContainer ? pipelineContainer.offsetHeight : 550;
    const stickyTop = 96;

    // Total scroll distance during which container remains sticky
    const maxScroll = runwayHeight - containerHeight;
    if (maxScroll <= 0) return;

    // How far user has scrolled into the sticky zone
    const scrolledDistance = stickyTop - rect.top;
    const progress = Math.max(0, Math.min(1, scrolledDistance / maxScroll));

    // Update progress bar
    if (pipelineProgressBar) {
      pipelineProgressBar.style.width = (progress * 100).toFixed(1) + "%";
    }

    // 4 stages mapped across progress:
    // 0.00 - 0.28: Stage 0 (STAGE 01)
    // 0.28 - 0.55: Stage 1 (STAGE 02)
    // 0.55 - 0.82: Stage 2 (STAGE 03)
    // 0.82 - 1.00: Stage 3 (STAGE 04)
    let activeIndex = 0;
    if (progress >= 0.82) {
      activeIndex = 3;
    } else if (progress >= 0.55) {
      activeIndex = 2;
    } else if (progress >= 0.28) {
      activeIndex = 1;
    } else {
      activeIndex = 0;
    }

    setStage(activeIndex);
  }

  // Mobile / Reduced Motion: IntersectionObserver for pipeline steps
  if (storySteps.length > 0 && (isMobile || prefersReducedMotion)) {
    const mobileObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const stepIndex = parseInt(entry.target.getAttribute("data-step"), 10) - 1;
          setStage(stepIndex);
        }
      });
    }, { threshold: 0.4 });

    storySteps.forEach(step => mobileObserver.observe(step));
  }

  // ==========================================================================
  // UNIFIED SCROLL ANIMATION ENGINE (Master Engine / Standalone Fallback)
  // ==========================================================================
  function onScrollTick() {
    updateHeroParallax();
    updatePipelineProgress();
  }

  if (motionEngine && !isPhase7Immersive) {
    // Coordinated via Master Motion Engine
    motionEngine.registerScene("phase6-hero-pipeline", {
      runAlways: true,
      onTick: onScrollTick
    });
  } else if (!motionEngine && !isPhase7Immersive) {
    // Standalone fallback
    let isScrollScheduled = false;
    window.addEventListener("scroll", () => {
      if (!isScrollScheduled) {
        requestAnimationFrame(() => {
          onScrollTick();
          isScrollScheduled = false;
        });
        isScrollScheduled = true;
      }
    }, { passive: true });
  }

  // Initial render pass
  onScrollTick();

  // ==========================================================================
  // 6. TEMPLATE SHOWCASE — Cinematic Crossfade
  // ==========================================================================
  const templateTabs = document.querySelectorAll(".showcase-template-tab");
  const showcasePreview = document.getElementById("showcaseTemplateFrame");

  function switchTemplateShowcase(templateName) {
    if (!showcasePreview) return;

    templateTabs.forEach(t => {
      if (t.getAttribute("data-template") === templateName) {
        t.classList.add("active");
      } else {
        t.classList.remove("active");
      }
    });

    if (prefersReducedMotion) {
      showcasePreview.className = "showcase-preview-box template-" + templateName;
      return;
    }

    // Crossfade: fade & slight scale out -> swap class -> fade & scale in
    showcasePreview.classList.add("transitioning-out");
    setTimeout(() => {
      showcasePreview.className = "showcase-preview-box template-" + templateName + " transitioning-in";
      // Force layout reflow
      void showcasePreview.offsetHeight;
      requestAnimationFrame(() => {
        showcasePreview.classList.remove("transitioning-in");
      });
    }, 200);
  }

  if (templateTabs.length > 0 && showcasePreview) {
    templateTabs.forEach(tab => {
      tab.addEventListener("click", () => {
        const templateName = tab.getAttribute("data-template");
        switchTemplateShowcase(templateName);
      });
    });
  }

  // ==========================================================================
  // 7. BENTO GRID — Scroll Reveal with Stagger (IntersectionObserver)
  // ==========================================================================
  const bentoCards = document.querySelectorAll(".bento-card, .bento-cell");

  if (bentoCards.length > 0 && "IntersectionObserver" in window && !prefersReducedMotion) {
    document.body.classList.add("has-scroll-reveal");

    const bentoObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add("revealed");
          bentoObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: "0px 0px 50px 0px" });

    bentoCards.forEach(card => bentoObserver.observe(card));
  } else {
    // Reveal all cards immediately
    bentoCards.forEach(card => card.classList.add("revealed"));
  }

  // ==========================================================================
  // 8. SMOOTH SCROLLING FOR INTERNAL LINKS (Respecting fixed navbar)
  // ==========================================================================
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      const targetId = this.getAttribute("href");
      if (targetId && targetId !== "#") {
        const targetElem = document.querySelector(targetId);
        if (targetElem) {
          e.preventDefault();
          targetElem.scrollIntoView({ behavior: prefersReducedMotion ? "auto" : "smooth" });
        }
      }
    });
  });

  // ==========================================================================
  // 9. MOBILE NAVIGATION TOGGLE
  // ==========================================================================
  const mobileNavBtn = document.getElementById("mobileNavToggle");
  const mobileNavMenu = document.getElementById("mobileNavMenu");
  if (mobileNavBtn && mobileNavMenu) {
    mobileNavBtn.addEventListener("click", () => {
      mobileNavMenu.classList.toggle("open");
      mobileNavBtn.setAttribute("aria-expanded", mobileNavMenu.classList.contains("open"));
    });
  }

  // ==========================================================================
  // 10. URL PARAMETER OVERRIDES (for Deterministic Testing & Direct Linking)
  // ==========================================================================
  const urlParams = new URLSearchParams(window.location.search);
  const scrollParam = urlParams.get("scroll");
  if (scrollParam) {
    const scrollY = parseInt(scrollParam, 10);
    if (!isNaN(scrollY)) {
      window.scrollTo({ top: scrollY, behavior: "auto" });
      onScrollTick();
    }
  }

  const stageParam = urlParams.get("stage");
  if (stageParam) {
    const stageIdx = parseInt(stageParam, 10) - 1;
    if (!isNaN(stageIdx) && stageIdx >= 0 && stageIdx < storySteps.length) {
      setStage(stageIdx);
    }
  }

  const templateParam = urlParams.get("template");
  if (templateParam) {
    switchTemplateShowcase(templateParam);
  }

})();
