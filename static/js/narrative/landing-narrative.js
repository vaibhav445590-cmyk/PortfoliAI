/**
 * PortfoliAI — Immersive Landing Narrative Coordinator (Phase 7D)
 * Orchestrates Acts I–V using the Phase 7C Unified Motion Engine:
 *   Act I: The Artifact (Interactive 3D document, pointer tilt, real drag-and-drop ingest)
 *   Act II: The Decomposition (Singularity collapse, spatial entity streaming)
 *   Act III: The Dual Identity (Pointer-driven interactive reveal mask)
 *   Act IV: The Archetype Workbench (3D perspective spatial carousel)
 *   Act V: The Living Portfolio (Full-bleed emerging portfolio showcase)
 */

(function () {
  'use strict';

  function initLandingNarrative() {
    const motion = window.PortfoliAIMotion;
    if (!motion) {
      console.warn('[PortfoliAI] Motion engine not loaded; skipping immersive narrative binding.');
      return;
    }

    const hudActBadge = document.getElementById('hudActBadge');
    const hudScrollPercent = document.getElementById('hudScrollPercent');
    const resumeCard = document.getElementById('hero3DResume');
    const fileInput = document.getElementById('resumeFileInput');
    const dropZone = document.getElementById('artifactDropZone');

    // ========================================================================
    // 1. ACT I — THE ARTIFACT CONTROLLER
    // ========================================================================
    if (resumeCard) {
      // Interactive Drag & Drop Handling
      if (dropZone && fileInput) {
        dropZone.addEventListener('click', () => fileInput.click());

        ['dragenter', 'dragover'].forEach(evt => {
          resumeCard.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            resumeCard.classList.add('drop-active');
          });
        });

        ['dragleave', 'drop'].forEach(evt => {
          resumeCard.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            resumeCard.classList.remove('drop-active');
          });
        });

        resumeCard.addEventListener('drop', (e) => {
          const files = e.dataTransfer.files;
          if (files && files.length > 0) {
            handleFileUpload(files[0]);
          }
        });

        fileInput.addEventListener('change', () => {
          if (fileInput.files && fileInput.files.length > 0) {
            handleFileUpload(fileInput.files[0]);
          }
        });
      }

      function handleFileUpload(file) {
        const dropPrompt = dropZone.querySelector('.drop-prompt');
        if (dropPrompt) dropPrompt.textContent = `INGESTING: ${file.name}...`;

        const formData = new FormData();
        formData.append('resume', file);

        fetch('/api/v1/resume/upload', {
          method: 'POST',
          body: formData
        })
        .then(res => res.json())
        .then(data => {
          if (data.success && data.data) {
            if (dropPrompt) dropPrompt.textContent = 'INGESTION COMPLETE · 100% FIDELITY';
            // Update candidate name & headline if extracted
            const nameEl = document.querySelector('.artifact-name');
            const roleEl = document.querySelector('.artifact-role');
            if (nameEl && data.data.name) nameEl.textContent = data.data.name;
            if (roleEl && data.data.headline) roleEl.textContent = data.data.headline;
            window.dispatchEvent(new CustomEvent('portfoliai:resume-updated', {
              detail: { name: data.data.name, headline: data.data.headline }
            }));
          } else {
            if (dropPrompt) dropPrompt.textContent = 'INGESTION FAILED · PLEASE RETRY';
          }
        })
        .catch(err => {
          console.warn('Resume upload error:', err);
          if (dropPrompt) dropPrompt.textContent = 'INGESTION READY (LOCAL MODE)';
        });
      }

      // Act I Motion Scene
      // Act I Motion Scene
      const act1Stage = document.querySelector('#act-artifact .act-stage');
      const act1Editorial = document.querySelector('.act1-editorial');
      motion.registerScene('act-1-artifact', {
        element: '#act-artifact',
        isSticky: true,
        onTick: ({ progress, pointer, reducedMotion }) => {
          const isMobile = window.innerWidth < 768;
          if (reducedMotion || isMobile) {
            resumeCard.style.transform = 'none';
            if (act1Stage) { act1Stage.style.opacity = '1'; act1Stage.style.transform = 'none'; }
            if (act1Editorial) { act1Editorial.style.opacity = '1'; act1Editorial.style.transform = 'none'; }
            return;
          }

          // Pointer Tilt (smooth damped cursor response)
          const tiltX = (pointer.dampedY || 0) * -8;
          const tiltY = (pointer.dampedX || 0) * 8;

          // Scroll Scrubbing: document recedes smoothly and centers as origami collapses into data core
          const scrollScale = 1 - progress * 0.08;
          const scrollY = progress * 20;

          resumeCard.style.transform = `perspective(1000px) rotateX(${tiltX.toFixed(2)}deg) rotateY(${tiltY.toFixed(2)}deg) scale3d(${scrollScale.toFixed(3)}, ${scrollScale.toFixed(3)}, 1) translateY(${scrollY.toFixed(1)}px)`;

          // Editorial text smoothly glides up and softens in final 30% of scroll to guide gaze directly to glowing core
          if (act1Editorial) {
            if (progress > 0.70) {
              const fade = motion.utils.clamp((progress - 0.70) / 0.25, 0, 1);
              const eased = motion.utils.easing.easeInOutQuad(fade);
              act1Editorial.style.opacity = (1 - eased * 0.65).toFixed(3);
              act1Editorial.style.transform = `translateY(${(-eased * 24).toFixed(1)}px)`;
            } else {
              act1Editorial.style.opacity = '1';
              act1Editorial.style.transform = 'none';
            }
          }

          // Stage maintains full opacity — Act 2 slides up seamlessly over it
          if (act1Stage) {
            act1Stage.style.opacity = '1';
          }
        }
      });
    }

    // ========================================================================
    // 2. ACT II — THE DECOMPOSITION CONTROLLER
    // ========================================================================
    const act2Stage = document.querySelector('#act-decomposition .act-stage');
    const singularityCore = document.querySelector('.singularity-core');
    const decompTracks = document.querySelectorAll('.decomp-track');

    if (singularityCore) {
      motion.registerScene('act-2-decomposition', {
        element: '#act-decomposition',
        isSticky: true,
        onTick: ({ progress, pointer, reducedMotion }) => {
          const isMobile = window.innerWidth < 768;
          if (reducedMotion || isMobile) {
            if (act2Stage) { act2Stage.style.opacity = '1'; act2Stage.style.transform = 'none'; }
            if (singularityCore) singularityCore.style.transform = 'scale(1)';
            decompTracks.forEach(track => { track.style.opacity = '1'; track.style.transform = 'none'; });
            return;
          }

          // Stage maintains solid opacity — zero blackouts/dead zones
          if (act2Stage) {
            act2Stage.style.opacity = '1';
          }

          // Singularity node pulses and scales across active progress
          const normP = motion.utils.clamp((progress - 0.05) / 0.90, 0, 1);
          const coreScale = 0.92 + Math.sin(normP * Math.PI) * 0.28;
          singularityCore.style.transform = `scale(${coreScale.toFixed(3)})`;

          // Outer pulse ring expands toward end of Act 2, projecting outward into the Act 3 radar portal
          const orbitRing = singularityCore.querySelector('.singularity-orbit-ring');
          if (orbitRing) {
            if (progress > 0.70) {
              const expand = (progress - 0.70) / 0.30;
              const ringScale = 1.0 + expand * 1.5;
              orbitRing.style.transform = `scale(${ringScale.toFixed(3)})`;
              orbitRing.style.opacity = (1 - expand * 0.4).toFixed(3);
            } else {
              orbitRing.style.transform = 'scale(1)';
              orbitRing.style.opacity = '1';
            }
          }

          // Staggered expansion of radial tracks from center outward
          decompTracks.forEach((track, idx) => {
            const trackOffset = 0.08 + (idx * 0.09);
            const trackProgress = motion.utils.clamp((progress - trackOffset) / 0.50, 0, 1);
            const eased = motion.utils.easing.easeOutExpo(trackProgress);

            track.style.opacity = eased.toFixed(3);
            track.style.transform = `scale(${0.86 + eased * 0.14}) translateY(${(1 - eased) * 22}px)`;
          });
        }
      });
    }

    // ========================================================================
    // 3. ACT III — THE DUAL IDENTITY CONTROLLER
    // ========================================================================
    const act3Stage = document.querySelector('#act-identity .act-stage');
    const identityStage = document.querySelector('.identity-focal-stage');
    const identityLayerPro = document.querySelector('.identity-layer-pro');

    if (identityStage && identityLayerPro) {
      identityStage.addEventListener('mousemove', (e) => {
        const rect = identityStage.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        identityLayerPro.style.setProperty('--reveal-x', `${x}px`);
        identityLayerPro.style.setProperty('--reveal-y', `${y}px`);
      });

      identityStage.addEventListener('mouseleave', () => {
        identityLayerPro.style.setProperty('--reveal-x', '50%');
        identityLayerPro.style.setProperty('--reveal-y', '50%');
      });

      // Odometer Figure Animation Engine
      let odometersTriggered = false;
      function triggerOdometers() {
        if (odometersTriggered) return;
        odometersTriggered = true;

        const figures = document.querySelectorAll('.odometer-figure[data-odometer-target]');
        figures.forEach(fig => {
          const target = parseFloat(fig.getAttribute('data-odometer-target')) || 0;
          const prefix = fig.getAttribute('data-prefix') || '';
          const suffix = fig.getAttribute('data-suffix') || '';
          const isDecimal = String(target).includes('.');

          if (window.gsap) {
            const proxy = { val: 0 };
            window.gsap.to(proxy, {
              val: target,
              duration: 1.6,
              ease: 'power2.out',
              onUpdate: () => {
                const displayVal = isDecimal ? proxy.val.toFixed(1) : Math.round(proxy.val);
                fig.textContent = `${prefix}${displayVal}${suffix}`;
              }
            });
          } else {
            fig.textContent = `${prefix}${target}${suffix}`;
          }
        });

        // Stagger in entity burst items
        const burstItems = document.querySelectorAll('.entity-burst-item');
        if (burstItems.length > 0 && window.gsap) {
          window.gsap.fromTo(burstItems, 
            { opacity: 0, x: -12 },
            { opacity: 1, x: 0, duration: 0.6, stagger: 0.12, ease: 'power2.out' }
          );
        }
      }

      motion.registerScene('act-3-identity', {
        element: '#act-identity',
        isSticky: true,
        onTick: ({ progress, pointer, reducedMotion }) => {
          const isMobile = window.innerWidth < 768;
          if (reducedMotion || isMobile) {
            if (act3Stage) { act3Stage.style.opacity = '1'; act3Stage.style.transform = 'none'; }
            if (identityStage) identityStage.style.transform = 'scale(1)';
            triggerOdometers();
            return;
          }

          // Trigger dynamic odometer telemetry
          if (progress > 0.02) {
            triggerOdometers();
          } else if (progress <= 0.005) {
            odometersTriggered = false;
          }

          // Stage maintains solid opacity
          if (act3Stage) {
            act3Stage.style.opacity = '1';
          }

          // Concentric radar portal subtle breathing and pointer tracking
          const scale = 0.98 + Math.sin(progress * Math.PI) * 0.04;
          const tiltX = (pointer.dampedY || 0) * -5;
          const tiltY = (pointer.dampedX || 0) * 5;
          identityStage.style.transform = `perspective(800px) rotateX(${tiltX.toFixed(2)}deg) rotateY(${tiltY.toFixed(2)}deg) scale(${scale.toFixed(3)})`;
        }
      });
    }

    // ========================================================================
    // 4. ACT IV — THE ARCHETYPE WORKBENCH CONTROLLER
    // ========================================================================
    const act4Stage = document.querySelector('#act-archetypes .act-stage');
    const archetypeCards = document.querySelectorAll('.archetype-card');
    const btnPrevArchetype = document.getElementById('btnPrevArchetype');
    const btnNextArchetype = document.getElementById('btnNextArchetype');
    let currentArchetypeIdx = 1; // Default to Glass (Index 1)

    function updateArchetypeCarousel() {
      archetypeCards.forEach((card, idx) => {
        card.classList.remove('active', 'prev', 'next', 'far-prev', 'far-next');

        const diff = idx - currentArchetypeIdx;
        if (diff === 0) {
          card.classList.add('active');
        } else if (diff === -1) {
          card.classList.add('prev');
        } else if (diff === 1) {
          card.classList.add('next');
        } else if (diff < -1) {
          card.classList.add('far-prev');
        } else if (diff > 1) {
          card.classList.add('far-next');
        }
      });

      // Update Living Portfolio template in Act V
      const activeCard = archetypeCards[currentArchetypeIdx];
      if (activeCard) {
        const selectedTemplate = activeCard.getAttribute('data-template') || 'glass';
        const portfolioFrame = document.querySelector('.portfolio-showcase-frame');
        if (portfolioFrame) {
          portfolioFrame.setAttribute('data-template', selectedTemplate);
        }
      }
    }

    if (archetypeCards.length > 0) {
      archetypeCards.forEach((card, idx) => {
        card.addEventListener('click', () => {
          currentArchetypeIdx = idx;
          updateArchetypeCarousel();
        });
      });

      if (btnPrevArchetype) {
        btnPrevArchetype.addEventListener('click', () => {
          currentArchetypeIdx = (currentArchetypeIdx - 1 + archetypeCards.length) % archetypeCards.length;
          updateArchetypeCarousel();
        });
      }

      if (btnNextArchetype) {
        btnNextArchetype.addEventListener('click', () => {
          currentArchetypeIdx = (currentArchetypeIdx + 1) % archetypeCards.length;
          updateArchetypeCarousel();
        });
      }

      updateArchetypeCarousel();

      motion.registerScene('act-4-archetypes', {
        element: '#act-archetypes',
        isSticky: true,
        onTick: ({ progress, pointer, reducedMotion }) => {
          const isMobile = window.innerWidth < 768;
          if (reducedMotion || isMobile) {
            if (act4Stage) { act4Stage.style.opacity = '1'; act4Stage.style.transform = 'none'; }
            return;
          }

          if (act4Stage) {
            act4Stage.style.opacity = '1';
          }

          // Subtle pointer tilt on the active card for tactile physical feel
          const activeCard = document.querySelector('.archetype-card.active');
          if (activeCard) {
            const tiltX = (pointer.dampedY || 0) * -6;
            const tiltY = (pointer.dampedX || 0) * 8;
            // As user scrolls towards the end of Act 4, active card smoothly expands toward camera
            let zBonus = 80;
            let scaleBonus = 1.06;
            if (progress > 0.75) {
              const expand = (progress - 0.75) / 0.25;
              zBonus += expand * 40;
              scaleBonus += expand * 0.06;
            }
            activeCard.style.transform = `translate3d(0, 0, ${zBonus}px) rotateX(${tiltX.toFixed(2)}deg) rotateY(${tiltY.toFixed(2)}deg) scale(${scaleBonus.toFixed(3)})`;
          }
        }
      });
    }

    // ========================================================================
    // 5. ACT V — THE LIVING PORTFOLIO CONTROLLER
    // ========================================================================
    const act5Scene = document.getElementById('act-portfolio');
    if (act5Scene) {
      motion.registerScene('act-5-portfolio', {
        element: '#act-portfolio',
        onTick: ({ progress }) => {
          // Portfolio emergence hook
        }
      });
    }

    // ========================================================================
    // 6. GLOBAL HUD TELEMETRY COORDINATOR (Zero Layout Thrashing)
    // ========================================================================
    const actElements = [
      { id: 'act-artifact', label: 'ACT 01 // THE ARTIFACT' },
      { id: 'act-decomposition', label: 'ACT 02 // THE DECOMPOSITION' },
      { id: 'act-identity', label: 'ACT 03 // THE DUAL IDENTITY' },
      { id: 'act-archetypes', label: 'ACT 04 // THE ARCHETYPE WORKBENCH' },
      { id: 'act-portfolio', label: 'ACT 05 // THE LIVING PORTFOLIO' }
    ];

    motion.registerScene('landing-hud-telemetry', {
      runAlways: true,
      onTick: ({ scroll }) => {
        // Update percentage progress: 000% to 100%
        if (hudScrollPercent) {
          const pct = Math.round(scroll.progress * 100);
          hudScrollPercent.textContent = `${String(pct).padStart(3, '0')}%`;
        }

        // Determine currently visible act using cached geometry & smoothed scroll
        if (hudActBadge) {
          let activeLabel = actElements[0].label;
          const currentDocY = scroll.currentY + window.innerHeight * 0.45;

          for (let i = 0; i < actElements.length; i++) {
            const el = document.getElementById(actElements[i].id);
            if (el) {
              const geom = motion.elementGeometry ? motion.elementGeometry.get(el) : null;
              if (geom && currentDocY >= geom.top && currentDocY <= geom.bottom) {
                activeLabel = actElements[i].label;
                break;
              }
            }
          }
          if (hudActBadge.textContent !== activeLabel) {
            hudActBadge.textContent = activeLabel;
          }
        }
      }
    });

    // Direct Linking & Deterministic Testing via ?act=1..5
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const actParam = urlParams.get('act');
      if (actParam) {
        const actIndex = parseInt(actParam, 10) - 1;
        if (actIndex >= 0 && actIndex < actElements.length) {
          const targetAct = document.getElementById(actElements[actIndex].id);
          if (targetAct) {
            setTimeout(() => {
              targetAct.scrollIntoView({ behavior: 'auto' });
            }, 50);
          }
        }
      }
    } catch (e) {}

    console.info('[PortfoliAI] Acts I–V Immersive Narrative bound to Motion Engine.');
  }

  // Bind on DOMContentLoaded or immediately if DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLandingNarrative);
  } else {
    initLandingNarrative();
  }
})();
