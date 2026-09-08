/**
 * PortfoliAI — Studio Canvas Controller (Phase 7F)
 * Manages the interactive center design surface, device framing (Desktop/Tablet/Mobile),
 * zoom controls, click-to-inspect focus, and live portfolio rendering.
 */

(function () {
  'use strict';

  class StudioCanvas {
    constructor() {
      this.device = 'desktop';
      this.zoom = 1.0;
      this.deviceFrame = null;
      this.innerScroll = null;
      this.zoomDisplay = null;
      this.selectedElement = null;
    }

    init() {
      this.deviceFrame = document.getElementById('studioDeviceFrame');
      this.innerScroll = document.getElementById('previewFrameInner') || document.getElementById('studioFrameBody');
      this.zoomDisplay = document.getElementById('studioZoomValue');

      this.bindDeviceButtons();
      this.bindZoomControls();
      this.bindCanvasInspect();
      this.renderLivePreview();

      console.info('[PortfoliAI Studio] Canvas Controller initialized.');
    }

    bindDeviceButtons() {
      const deviceBtns = document.querySelectorAll('.studio-device-btn');
      deviceBtns.forEach(btn => {
        btn.addEventListener('click', () => {
          const targetDevice = btn.getAttribute('data-device');
          this.setDevice(targetDevice);
          deviceBtns.forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
        });
      });
    }

    setDevice(device) {
      this.device = device;
      if (this.deviceFrame) {
        this.deviceFrame.setAttribute('data-device', device);
      }
      const label = document.getElementById('studioDeviceLabel');
      if (label) {
        label.textContent = device === 'desktop' ? 'DESKTOP · 1200PX' :
                            device === 'tablet' ? 'TABLET · 768PX' : 'MOBILE · 390PX';
      }
    }

    bindZoomControls() {
      const btnZoomIn = document.getElementById('btnStudioZoomIn');
      const btnZoomOut = document.getElementById('btnStudioZoomOut');
      const btnZoomReset = document.getElementById('btnStudioZoomReset');

      if (btnZoomIn) {
        btnZoomIn.addEventListener('click', () => this.adjustZoom(0.1));
      }
      if (btnZoomOut) {
        btnZoomOut.addEventListener('click', () => this.adjustZoom(-0.1));
      }
      if (btnZoomReset) {
        btnZoomReset.addEventListener('click', () => this.setZoom(1.0));
      }
    }

    adjustZoom(delta) {
      const newZoom = Math.min(Math.max(this.zoom + delta, 0.5), 1.5);
      this.setZoom(newZoom);
    }

    setZoom(val) {
      this.zoom = parseFloat(val.toFixed(2));
      if (this.deviceFrame) {
        this.deviceFrame.style.transform = `scale(${this.zoom})`;
      }
      if (this.zoomDisplay) {
        this.zoomDisplay.textContent = `${Math.round(this.zoom * 100)}%`;
      }
    }

    bindCanvasInspect() {
      // Allow clicking inside canvas items to focus in inspector
      if (this.innerScroll) {
        this.innerScroll.addEventListener('click', (e) => {
          const projectCard = e.target.closest('[data-project-id]');
          if (projectCard && window.PortfoliAIStudioInspector) {
            const projectId = projectCard.getAttribute('data-project-id');
            window.PortfoliAIStudioInspector.selectProject(projectId);
            return;
          }

          const headerEl = e.target.closest('.portfolio-header, .glass-header');
          if (headerEl && window.PortfoliAIStudioInspector) {
            window.PortfoliAIStudioInspector.showProfileInspector();
          }
        });
      }
    }

    renderLivePreview() {
      if (window.PortfoliAIPreview && typeof window.PortfoliAIPreview.renderLivePreview === 'function') {
        window.PortfoliAIPreview.renderLivePreview();
      }
    }
  }

  window.PortfoliAIStudioCanvas = new StudioCanvas();

  document.addEventListener('DOMContentLoaded', () => {
    window.PortfoliAIStudioCanvas.init();
  });
})();
