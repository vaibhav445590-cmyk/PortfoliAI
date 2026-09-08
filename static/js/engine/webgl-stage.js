/**
 * PortfoliAI — Shared WebGL Stage (Phase 7E)
 * Manages a single WebGLRenderer instance across multiple narrative acts
 * using viewport/scissor testing over DOM placeholder coordinates.
 *
 * Coordinates directly with window.PortfoliAIMotion.
 */

(function () {
  'use strict';

  class WebGLStage {
    constructor() {
      this.canvas = null;
      this.renderer = null;
      this.isSupported = false;
      this.isInitialized = false;
      this.scenes = new Map();
      this.activeScenesCount = 0;
      this.dpr = 1;
      this.width = window.innerWidth;
      this.height = window.innerHeight;
      this.readyPromise = null;
    }

    /**
     * Dynamically loads Three.js if not present on window.
     */
    async loadThree() {
      if (window.THREE) return window.THREE;
      if (this.readyPromise) return this.readyPromise;

      this.readyPromise = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = '/static/js/vendor/three.min.js';
        script.async = true;
        script.onload = () => {
          console.info('[PortfoliAI WebGL] Three.js loaded successfully.');
          resolve(window.THREE);
        };
        script.onerror = (err) => {
          console.warn('[PortfoliAI WebGL] Failed to load Three.js vendor script:', err);
          reject(err);
        };
        document.head.appendChild(script);
      });

      return this.readyPromise;
    }

    /**
     * Checks if WebGL context can be created.
     */
    checkWebGLSupport() {
      try {
        const testCanvas = document.createElement('canvas');
        return !!(window.WebGLRenderingContext &&
          (testCanvas.getContext('webgl') || testCanvas.getContext('experimental-webgl')));
      } catch (e) {
        return false;
      }
    }

    /**
     * Initializes the shared WebGL canvas and renderer.
     */
    async init() {
      if (this.isInitialized) return true;

      if (!this.checkWebGLSupport()) {
        console.warn('[PortfoliAI WebGL] WebGL not supported on this device. Fallbacks active.');
        this.markFallback();
        return false;
      }

      try {
        await this.loadThree();
      } catch (e) {
        this.markFallback();
        return false;
      }

      const THREE = window.THREE;
      if (!THREE) {
        this.markFallback();
        return false;
      }

      this.canvas = document.getElementById('immWebGLCanvas');
      if (!this.canvas) {
        this.canvas = document.createElement('canvas');
        this.canvas.id = 'immWebGLCanvas';
        this.canvas.className = 'imm-webgl-canvas';
        this.canvas.setAttribute('aria-hidden', 'true');
        const root = document.getElementById('immersiveNarrative') || document.body;
        root.appendChild(this.canvas);
      }

      // Compute clamped DPR (max 1.5 to 1.75 to protect mobile/laptop thermal efficiency)
      const rawDPR = window.devicePixelRatio || 1;
      this.dpr = Math.min(rawDPR, 1.75);

      try {
        this.renderer = new THREE.WebGLRenderer({
          canvas: this.canvas,
          alpha: true,
          antialias: true,
          powerPreference: 'high-performance'
        });
        this.renderer.setPixelRatio(this.dpr);
        this.renderer.setSize(this.width, this.height, false);
        this.renderer.setClearColor(0x000000, 0);
        this.renderer.setScissorTest(true);

        this.isSupported = true;
        this.isInitialized = true;
        document.body.classList.add('webgl-active');
        console.info('[PortfoliAI WebGL] Shared WebGL Stage initialized with DPR:', this.dpr);

        // Bind resize
        window.addEventListener('resize', () => this.handleResize(), { passive: true });

        // Hook into Motion Engine
        if (window.PortfoliAIMotion) {
          window.PortfoliAIMotion.registerScene('webgl-stage-controller', {
            runAlways: true,
            onTick: (engineState) => this.render(engineState)
          });
        }

        return true;
      } catch (err) {
        console.error('[PortfoliAI WebGL] WebGLRenderer creation error:', err);
        this.markFallback();
        return false;
      }
    }

    markFallback() {
      this.isSupported = false;
      document.body.classList.add('webgl-fallback');
      document.body.classList.remove('webgl-active');
    }

    handleResize() {
      if (!this.renderer) return;
      this.width = window.innerWidth;
      this.height = window.innerHeight;
      this.renderer.setSize(this.width, this.height, false);

      this.scenes.forEach(sceneDef => {
        if (sceneDef.onResize) {
          sceneDef.onResize(this.width, this.height);
        }
      });
    }

    /**
     * Registers a sub-scene to render inside a specific DOM element's viewport.
     */
    registerScene(id, config) {
      // config: { element, scene, camera, onTick, onResize, setup, dispose }
      this.scenes.set(id, {
        id,
        element: typeof config.element === 'string' ? document.querySelector(config.element) : config.element,
        scene: config.scene,
        camera: config.camera,
        onTick: config.onTick || null,
        onResize: config.onResize || null,
        dispose: config.dispose || null,
        enabled: true,
        isVisible: false
      });
    }

    unregisterScene(id) {
      const sceneDef = this.scenes.get(id);
      if (sceneDef) {
        if (sceneDef.dispose) sceneDef.dispose();
        this.scenes.delete(id);
      }
    }

    /**
     * Centralized render pass: iterates over registered scenes,
     * calculates viewport/scissor coordinates, and renders.
     */
    render(engineState) {
      if (!this.renderer || !this.isSupported || document.hidden) return;

      const { deltaTime, pointer, reducedMotion } = engineState;

      // Always clear the shared canvas to transparent each frame
      // This guarantees that egressed scenes or inactive regions leave zero ghost pixels/bleed
      this.renderer.setScissorTest(false);
      this.renderer.clear();
      this.renderer.setScissorTest(true);

      this.scenes.forEach(sceneDef => {
        if (!sceneDef.enabled || !sceneDef.element || !sceneDef.scene || !sceneDef.camera) return;

        const rect = sceneDef.element.getBoundingClientRect();

        // Viewport intersection test
        const isVisible = (
          rect.bottom >= 0 &&
          rect.top <= this.height &&
          rect.right >= 0 &&
          rect.left <= this.width &&
          rect.width > 0 &&
          rect.height > 0
        );

        sceneDef.isVisible = isVisible;
        if (!isVisible) return;

        // Invert Y coordinate for WebGL viewport (WebGL bottom-left vs DOM top-left)
        const bottom = this.height - rect.bottom;
        const left = rect.left;
        const width = rect.width;
        const height = rect.height;

        this.renderer.setViewport(left, bottom, width, height);
        this.renderer.setScissor(left, bottom, width, height);

        // Update camera aspect
        if (sceneDef.camera.isPerspectiveCamera) {
          const currentAspect = width / height;
          if (Math.abs(sceneDef.camera.aspect - currentAspect) > 0.001) {
            sceneDef.camera.aspect = currentAspect;
            sceneDef.camera.updateProjectionMatrix();
          }
        }

        // Get normalized progress through parent act or element
        let progress = 0;
        let actRunway = null;
        if (window.PortfoliAIMotion && sceneDef.element) {
          actRunway = sceneDef.element.closest('.act-runway') || sceneDef.element;
          if (actRunway.classList.contains('act-runway')) {
            progress = window.PortfoliAIMotion.getStickyProgress(actRunway, engineState.scroll.currentY);
          } else {
            progress = window.PortfoliAIMotion.getSectionProgress(actRunway);
          }
        }

        // Maintain continuous visibility throughout the act runway; only softly fade at the true boundary (progress > 0.94)
        let egressFade = 1.0;
        if (progress > 0.94) {
          egressFade = Math.max(0, 1 - (progress - 0.94) / 0.06);
        }
        if (egressFade <= 0.005) {
          // Completely occluded/egressed: do not render to avoid bleeding over subsequent acts
          return;
        }

        if (sceneDef.onTick) {
          sceneDef.onTick({
            progress,
            pointer,
            deltaTime,
            reducedMotion,
            rect,
            renderer: this.renderer,
            egressFade
          });
        }

        this.renderer.render(sceneDef.scene, sceneDef.camera);
      });
    }

    dispose() {
      if (this.renderer) {
        this.scenes.forEach(sceneDef => {
          if (sceneDef.dispose) sceneDef.dispose();
        });
        this.scenes.clear();
        this.renderer.dispose();
        this.renderer = null;
      }
      if (this.canvas && this.canvas.parentNode) {
        this.canvas.parentNode.removeChild(this.canvas);
      }
      this.isInitialized = false;
    }
  }

  // Global singleton
  window.PortfoliAIWebGL = new WebGLStage();
})();
