/**
 * PortfoliAI — Studio Contextual Inspector (Phase 7F)
 * Coordinates right-hand contextual panel switching (Portfolio Settings / Selected Project / Profile),
 * live settings synchronization, project form persistence, and publish workflow.
 */

(function () {
  'use strict';

  class StudioInspector {
    constructor() {
      this.currentMode = 'portfolio'; // 'portfolio' | 'project' | 'profile'
      this.selectedProjectId = null;
      this.saveTimeout = null;
    }

    init() {
      this.bindArchetypeSelection();
      this.bindAccentSwatches();
      this.bindSectionToggles();
      this.bindProfileInputs();
      this.bindProjectInputs();
      this.bindPublishButton();
      this.bindRailProjectClicks();

      console.info('[PortfoliAI Studio] Contextual Inspector initialized.');
    }

    showPortfolioSettings() {
      this.showPortfolioInspector();
    }

    showProjectInspector(projectId) {
      this.selectProject(projectId);
    }

    applyArchetype(templateKey) {
      const card = document.querySelector(`.studio-archetype-choice[data-template="${templateKey}"]`);
      if (card) {
        card.click();
      }
    }

    showPortfolioInspector() {
      this.setPanel('panelPortfolioSettings');
      this.currentMode = 'portfolio';
      this.selectedProjectId = null;
      this.clearSelectedProjectHighlight();
    }

    showProfileInspector() {
      this.setPanel('panelProfileSettings');
      this.currentMode = 'profile';
      this.selectedProjectId = null;
      this.clearSelectedProjectHighlight();
    }

    selectProject(projectId) {
      this.selectedProjectId = projectId;
      this.currentMode = 'project';
      this.setPanel('panelProjectSettings');
      this.highlightSelectedProject(projectId);
      this.populateProjectForm(projectId);
    }

    bindRailProjectClicks() {
      document.addEventListener('click', (e) => {
        const editBtn = e.target.closest('.btn-edit-project');
        if (editBtn) {
          const pId = editBtn.getAttribute('data-project-id');
          if (pId) {
            this.selectProject(pId);
            return;
          }
        }
        const item = e.target.closest('.studio-project-item');
        if (item && !e.target.closest('button')) {
          const pId = item.getAttribute('data-project-id');
          if (pId) {
            this.selectProject(pId);
          }
        }
      });
    }

    setPanel(panelId) {
      const panels = document.querySelectorAll('.studio-inspector-panel');
      panels.forEach(p => {
        if (p.id === panelId) p.classList.add('active');
        else p.classList.remove('active');
      });
    }

    highlightSelectedProject(projectId) {
      document.querySelectorAll('.studio-project-item').forEach(el => {
        if (el.getAttribute('data-project-id') == projectId) {
          el.classList.add('selected');
        } else {
          el.classList.remove('selected');
        }
      });
    }

    clearSelectedProjectHighlight() {
      document.querySelectorAll('.studio-project-item').forEach(el => el.classList.remove('selected'));
    }

    populateProjectForm(projectId) {
      const ws = window.PortfoliAIWorkspace;
      let project = ws?.state?.projects ? ws.state.projects.find(p => p.id == projectId) : null;

      if (!project) {
        // Fallback to reading from DOM item
        const item = document.querySelector(`.studio-project-item[data-project-id="${projectId}"]`);
        if (item) {
          project = {
            id: projectId,
            title: item.querySelector('.studio-project-title')?.textContent?.trim() || 'Machine Learning System',
            category: item.querySelector('.studio-project-category')?.textContent?.trim() || 'AI & Machine Learning',
            description: 'Advanced distributed neural architecture with real-time vector embeddings, sub-millisecond inference, and production observability.',
            technologies: 'Python, PyTorch, FastAPI, Redis, Docker',
            github_url: 'https://github.com/developer/ml-system',
            live_url: 'https://ml-system.live'
          };
        }
      }

      if (!project) return;

      const fTitle = document.getElementById('inspProjTitle');
      const fCategory = document.getElementById('inspProjCategory');
      const fDesc = document.getElementById('inspProjDesc');
      const fTech = document.getElementById('inspProjTech');
      const fGithub = document.getElementById('inspProjGithub');
      const fLive = document.getElementById('inspProjLive');

      if (fTitle) fTitle.value = project.title || '';
      if (fCategory) fCategory.value = project.category || '';
      if (fDesc) fDesc.value = project.description || '';
      if (fTech) fTech.value = Array.isArray(project.technologies) ? project.technologies.join(', ') : (project.technologies || '');
      if (fGithub) fGithub.value = project.github_url || '';
      if (fLive) fLive.value = project.live_url || '';
    }

    bindArchetypeSelection() {
      const archetypeCards = document.querySelectorAll('.studio-archetype-choice');
      archetypeCards.forEach(card => {
        card.addEventListener('click', () => {
          archetypeCards.forEach(c => c.classList.remove('active'));
          card.classList.add('active');

          const template = card.getAttribute('data-template') || 'glass';

          // Sync with legacy template cards if present
          document.querySelectorAll('.template-choice-card').forEach(tc => {
            if (tc.getAttribute('data-template') === template) tc.classList.add('active');
            else tc.classList.remove('active');
          });

          this.triggerLivePreview();
          this.queueAutoSave();
        });
      });
    }

    bindAccentSwatches() {
      const swatches = document.querySelectorAll('.accent-swatch-btn');
      swatches.forEach(swatch => {
        swatch.addEventListener('click', () => {
          swatches.forEach(s => s.classList.remove('active'));
          swatch.classList.add('active');
          this.triggerLivePreview();
          this.queueAutoSave();
        });
      });
    }

    bindSectionToggles() {
      const toggles = document.querySelectorAll('[id^="toggleSec_"]');
      toggles.forEach(toggle => {
        toggle.addEventListener('change', () => {
          this.triggerLivePreview();
          this.queueAutoSave();
        });
      });
    }

    bindProfileInputs() {
      const inputs = ['custCustomName', 'custCustomHeadline', 'custCustomBio', 'custSocialGithub', 'custSocialLinkedin', 'custSocialTwitter'];
      inputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
          el.addEventListener('input', () => {
            this.triggerLivePreview();
            this.queueAutoSave();
          });
        }
      });
    }

    bindProjectInputs() {
      const btnSave = document.getElementById('btnInspSaveProject');
      const btnDelete = document.getElementById('btnInspDeleteProject');

      if (btnSave) {
        btnSave.addEventListener('click', async () => {
          if (!this.selectedProjectId) return;
          const ws = window.PortfoliAIWorkspace;
          if (!ws) return;

          const payload = {
            title: document.getElementById('inspProjTitle')?.value.trim(),
            category: document.getElementById('inspProjCategory')?.value.trim(),
            description: document.getElementById('inspProjDesc')?.value.trim(),
            technologies: document.getElementById('inspProjTech')?.value.trim(),
            github_url: document.getElementById('inspProjGithub')?.value.trim(),
            live_url: document.getElementById('inspProjLive')?.value.trim()
          };

          try {
            const resp = await fetch(`/api/v1/projects/${this.selectedProjectId}`, {
              method: 'PUT',
              headers: ws.getAuthHeaders(true),
              body: JSON.stringify(payload)
            });

            if (resp.ok) {
              ws.showToast('Project updated successfully');
              ws.loadWorkspaceData();
              this.triggerLivePreview();
            } else {
              ws.showToast('Failed to update project', 'error');
            }
          } catch (err) {
            console.error('Project update error:', err);
          }
        });
      }

      if (btnDelete) {
        btnDelete.addEventListener('click', async () => {
          if (!this.selectedProjectId) return;
          const ws = window.PortfoliAIWorkspace;
          if (!ws || !confirm('Are you sure you want to delete this project?')) return;

          try {
            const resp = await fetch(`/api/v1/projects/${this.selectedProjectId}`, {
              method: 'DELETE',
              headers: ws.getAuthHeaders(true)
            });

            if (resp.ok) {
              ws.showToast('Project deleted');
              this.showPortfolioInspector();
              ws.loadWorkspaceData();
              this.triggerLivePreview();
            } else {
              ws.showToast('Failed to delete project', 'error');
            }
          } catch (err) {
            console.error('Project delete error:', err);
          }
        });
      }
    }

    bindPublishButton() {
      const btnPublish = document.getElementById('btnStudioPublish');
      if (btnPublish) {
        btnPublish.addEventListener('click', () => {
          const ws = window.PortfoliAIWorkspace;
          if (!ws) return;

          // Set status to published
          const radPublished = document.getElementById('statusPublished');
          if (radPublished) radPublished.checked = true;

          btnPublish.textContent = 'Publishing...';
          ws.saveCustomization().then(() => {
            btnPublish.textContent = '✓ Published';
            const badge = document.getElementById('studioTelemetryStatus');
            if (badge) badge.textContent = 'STATUS: PUBLISHED · LIVE';
            setTimeout(() => {
              btnPublish.textContent = 'Publish Portfolio';
            }, 3000);
          }).catch(() => {
            btnPublish.textContent = 'Publish Failed';
          });
        });
      }
    }

    triggerLivePreview() {
      if (window.PortfoliAIPreview && typeof window.PortfoliAIPreview.renderLivePreview === 'function') {
        window.PortfoliAIPreview.renderLivePreview();
      }
    }

    queueAutoSave() {
      clearTimeout(this.saveTimeout);
      const statusPill = document.getElementById('studioSaveStatusPill');
      if (statusPill) statusPill.textContent = 'SAVING...';

      this.saveTimeout = setTimeout(async () => {
        const ws = window.PortfoliAIWorkspace;
        if (ws && typeof ws.saveCustomization === 'function') {
          await ws.saveCustomization();
          if (statusPill) statusPill.textContent = 'SAVED · LOCAL';
        }
      }, 1000);
    }
  }

  window.PortfoliAIStudioInspector = new StudioInspector();

  document.addEventListener('DOMContentLoaded', () => {
    window.PortfoliAIStudioInspector.init();
  });
})();
