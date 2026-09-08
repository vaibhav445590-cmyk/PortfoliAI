/**
 * PortfoliAI — Public Portfolio Interaction & Motion Coordinator (Phase 7G)
 * Lightweight, recruiter-focused client script for /p/<student_id>
 * - Active scroll navigation highlighting via IntersectionObserver
 * - Integration with window.PortfoliAIMotion when available
 * - Copy portfolio share URL with feedback
 * - Interactive skill tag click-to-filter / focus
 */

(function () {
  'use strict';

  function initPublicNavObserver() {
    const sections = document.querySelectorAll('section[id], header[id], div[id^="act-"], div[id="sec-projects"]');
    const navLinks = document.querySelectorAll('.pub-nav-link');
    if (!sections.length || !navLinks.length) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const id = entry.target.getAttribute('id');
          navLinks.forEach(link => {
            if (link.getAttribute('href') === '#' + id) {
              link.classList.add('active');
            } else {
              link.classList.remove('active');
            }
          });
        }
      });
    }, {
      rootMargin: '-20% 0px -70% 0px'
    });

    sections.forEach(sec => observer.observe(sec));
  }

  function initShareButton() {
    const shareBtns = document.querySelectorAll('.btn-share-portfolio, #btnCopyShareLink');
    shareBtns.forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.preventDefault();
        const url = window.location.href;
        try {
          if (navigator.clipboard) {
            await navigator.clipboard.writeText(url);
          } else {
            const input = document.createElement('input');
            input.value = url;
            document.body.appendChild(input);
            input.select();
            document.execCommand('copy');
            document.body.removeChild(input);
          }

          const orig = btn.innerHTML;
          btn.innerHTML = '✓ Copied Link!';
          setTimeout(() => {
            btn.innerHTML = orig;
          }, 2500);
        } catch (err) {
          console.error('Failed to copy portfolio URL:', err);
        }
      });
    });
  }

  function initSkillHighlighting() {
    const skillTags = document.querySelectorAll('.portfolio-skill-pill, .glass-chip, .minimal-tech-tag, .minimal-skill-keyword');
    const projectCards = document.querySelectorAll('.glass-case-panel, .minimal-project-entry, .modern-bento-card, .terminal-cli-case, .dark-case-panel');

    skillTags.forEach(tag => {
      tag.addEventListener('click', () => {
        const skillName = tag.textContent.trim().toLowerCase();
        
        projectCards.forEach(card => {
          const cardText = card.textContent.toLowerCase();
          if (cardText.includes(skillName)) {
            card.style.outline = '2px solid var(--portfolio-accent, #7c3aed)';
            card.style.outlineOffset = '4px';
            setTimeout(() => {
              card.style.outline = '';
              card.style.outlineOffset = '';
            }, 2000);
          }
        });
      });
    });
  }

  function initMotionEntrance() {
    if (window.PortfoliAIMotion) {
      document.querySelectorAll('.glass-case-panel, .minimal-project-entry, .modern-bento-card, .dark-case-panel').forEach(el => {
        el.style.opacity = '1';
      });
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    initPublicNavObserver();
    initShareButton();
    initSkillHighlighting();
    initMotionEntrance();
    console.info('[PortfoliAI] Public Portfolio engine initialized.');
  });
})();
