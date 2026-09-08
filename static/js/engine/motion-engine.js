/**
 * PortfoliAI — Master Motion Engine & Scroll Coordinator (Phase 7C)
 * ============================================================================
 * Centralized motion infrastructure providing:
 *   1. Single master requestAnimationFrame heartbeat
 *   2. Normalized scroll position, velocity, and section-level progress
 *   3. Framerate-independent interpolation (lerp, damp, easing primitives)
 *   4. Scene registration and lifecycle management
 *   5. Centralized IntersectionObserver for visibility-aware updates
 *   6. Centralized pointer and touch tracking with damping
 *   7. Batched resize management with DPR clamping
 *   8. Compositor-friendly DOM motion utilities
 *   9. Dynamic prefers-reduced-motion respect
 *  10. Development diagnostics and performance safeguards
 * ============================================================================
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.PortfoliAIMotion = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // --- Easing Functions Primitives ---
  const Easing = {
    linear: (t) => t,
    easeInQuad: (t) => t * t,
    easeOutQuad: (t) => t * (2 - t),
    easeInOutQuad: (t) => (t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t),
    easeInCubic: (t) => t * t * t,
    easeOutCubic: (t) => (--t) * t * t + 1,
    easeInOutCubic: (t) => (t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1),
    easeOutExpo: (t) => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t)),
    easeInOutCirc: (t) =>
      t < 0.5
        ? (1 - Math.sqrt(1 - Math.pow(2 * t, 2))) / 2
        : (Math.sqrt(1 - Math.pow(-2 * t + 2, 2)) + 1) / 2,
    easeOutBack: (t, s = 1.70158) => (--t) * t * ((s + 1) * t + s) + 1
  };

  // --- Math Utility Functions ---
  function clamp(val, min = 0, max = 1) {
    return Math.max(min, Math.min(max, val));
  }

  function lerp(start, end, factor) {
    return start + (end - start) * factor;
  }

  function damp(current, target, smoothing, dt) {
    // Framerate-independent damping using exponential decay
    return current + (target - current) * (1 - Math.exp(-smoothing * dt));
  }

  function mapRange(value, inMin, inMax, outMin, outMax, clampResult = true) {
    if (inMax === inMin) return outMin;
    const norm = (value - inMin) / (inMax - inMin);
    const mapped = outMin + norm * (outMax - outMin);
    return clampResult
      ? Math.max(Math.min(outMin, outMax), Math.min(Math.max(outMin, outMax), mapped))
      : mapped;
  }

  // --- Motion Engine Core ---
  class MotionEngine {
    constructor() {
      // Feature & Environment Flags
      this.reducedMotion = false;
      this.isMobile = false;
      this.isTablet = false;
      this.isDesktop = true;
      this.debug = false;

      // Master Animation Loop State
      this.isRunning = false;
      this.isPaused = false;
      this.rafId = null;
      this.lastTimestamp = 0;
      this.deltaTime = 0.016;
      this.elapsedTime = 0;
      this.frameCount = 0;
      this.fps = 60;
      this._fpsSmoothing = 0.1;

      // Scroll State
      this.scroll = {
        targetY: 0,
        currentY: 0,
        previousY: 0,
        velocity: 0,
        direction: 0, // 1 = down, -1 = up, 0 = idle
        progress: 0,  // 0.0 to 1.0 across document
        maxScroll: 0,
        isScrolling: false,
        damping: 10   // damping frequency for smooth scroll
      };

      // Pointer State
      this.pointer = {
        clientX: 0,
        clientY: 0,
        x: 0,          // Normalized -1 (left) to 1 (right), 0 = center
        y: 0,          // Normalized -1 (top) to 1 (bottom), 0 = center
        normX: 0.5,    // Normalized 0 (left) to 1 (right)
        normY: 0.5,    // Normalized 0 (top) to 1 (bottom)
        targetX: 0,
        targetY: 0,
        dampedX: 0,    // Smoothed X
        dampedY: 0,    // Smoothed Y
        prevX: 0,
        prevY: 0,
        velocityX: 0,
        velocityY: 0,
        isInside: true,
        isTouch: false,
        damping: 8     // pointer smoothing rate
      };

      // Viewport State
      this.viewport = {
        width: typeof window !== 'undefined' ? window.innerWidth : 1440,
        height: typeof window !== 'undefined' ? window.innerHeight : 900,
        dpr: typeof window !== 'undefined' ? Math.min(window.devicePixelRatio || 1, 2) : 1,
        aspectRatio: 1.6,
        documentHeight: 0
      };

      // Scene Registry
      this.scenes = new Map();

      // Cached Element Geometry (Zero Layout-Thrashing in Animation Loop)
      this.elementGeometry = new Map();

      // Shared Centralized Visibility Observer
      this.observer = null;

      // DOM Motion Utilities Bound to this instance
      this.utils = {
        clamp,
        lerp,
        damp,
        mapRange,
        easing: Easing,
        setTransform: this.setTransform.bind(this),
        setOpacity: this.setOpacity.bind(this),
        setBlur: this.setBlur.bind(this),
        setCSSVar: this.setCSSVar.bind(this),
        getStickyProgress: this.getStickyProgress.bind(this)
      };

      // Bound Event Handlers
      this._onTick = this._tick.bind(this);
      this._onScroll = this._handleScroll.bind(this);
      this._onScrollEnd = this._handleScrollEnd.bind(this);
      this._onPointerMove = this._handlePointerMove.bind(this);
      this._onPointerLeave = this._handlePointerLeave.bind(this);
      this._onTouchMove = this._handleTouchMove.bind(this);
      this._onResize = this._handleResize.bind(this);
      this._onVisibilityChange = this._handleVisibilityChange.bind(this);

      // Auto-initialize if in browser environment
      if (typeof window !== 'undefined') {
        this.init();
      }
    }

    // ========================================================================
    // 1. INITIALIZATION & LIFECYCLE
    // ========================================================================
    init() {
      if (typeof window === 'undefined') return this;

      // 1. Reduced Motion Preference
      const motionMedia = window.matchMedia('(prefers-reduced-motion: reduce)');
      this.reducedMotion = motionMedia.matches;
      try {
        motionMedia.addEventListener('change', (e) => {
          this.reducedMotion = e.matches;
          if (this.reducedMotion) {
            // Instantly snap damped values
            this.scroll.currentY = this.scroll.targetY;
            this.pointer.dampedX = this.pointer.targetX;
            this.pointer.dampedY = this.pointer.targetY;
          }
        });
      } catch (err) {
        // Fallback for older browsers
        motionMedia.addListener && motionMedia.addListener((e) => {
          this.reducedMotion = e.matches;
        });
      }

      // 2. Debug flag check from URL
      try {
        const params = new URLSearchParams(window.location.search);
        if (params.get('debug_motion') === '1' || params.get('debug') === 'motion') {
          this.debug = true;
          console.info('[PortfoliAIMotion] Debug diagnostics active.');
        }
      } catch (e) {}

      // 3. Measure initial viewport & scroll
      this._measureViewport();
      this.scroll.targetY = window.pageYOffset || document.documentElement.scrollTop || 0;
      this.scroll.currentY = this.scroll.targetY;
      this.scroll.previousY = this.scroll.targetY;

      // 4. Setup Centralized IntersectionObserver
      if ('IntersectionObserver' in window) {
        this.observer = new IntersectionObserver(
          (entries) => {
            entries.forEach((entry) => {
              const sceneId = entry.target.getAttribute('data-motion-scene');
              if (sceneId && this.scenes.has(sceneId)) {
                const scene = this.scenes.get(sceneId);
                const wasVisible = scene.isVisible;
                scene.isVisible = entry.isIntersecting;
                scene.intersectionRatio = entry.intersectionRatio;

                if (!wasVisible && entry.isIntersecting && typeof scene.onEnter === 'function') {
                  scene.onEnter({ entry, engine: this });
                } else if (wasVisible && !entry.isIntersecting && typeof scene.onLeave === 'function') {
                  scene.onLeave({ entry, engine: this });
                }
              }
            });
          },
          {
            threshold: [0, 0.25, 0.5, 0.75, 1.0],
            rootMargin: '100px 0px 100px 0px' // Graceful preload threshold
          }
        );
      }

      // 5. Attach Passive Event Listeners
      window.addEventListener('scroll', this._onScroll, { passive: true });
      if ('onscrollend' in window) {
        window.addEventListener('scrollend', this._onScrollEnd, { passive: true });
      } else {
        // Debounce fallback for scrollend
        this._scrollEndTimer = null;
      }

      window.addEventListener('pointermove', this._onPointerMove, { passive: true });
      window.addEventListener('pointerleave', this._onPointerLeave, { passive: true });
      window.addEventListener('touchmove', this._onTouchMove, { passive: true });
      window.addEventListener('resize', this._onResize, { passive: true });
      document.addEventListener('visibilitychange', this._onVisibilityChange);

      // 6. Start Master RAF Heartbeat
      this.start();

      return this;
    }

    destroy() {
      this.stop();
      if (typeof window !== 'undefined') {
        window.removeEventListener('scroll', this._onScroll);
        window.removeEventListener('scrollend', this._onScrollEnd);
        window.removeEventListener('pointermove', this._onPointerMove);
        window.removeEventListener('pointerleave', this._onPointerLeave);
        window.removeEventListener('touchmove', this._onTouchMove);
        window.removeEventListener('resize', this._onResize);
        document.removeEventListener('visibilitychange', this._onVisibilityChange);
      }
      if (this.observer) {
        this.observer.disconnect();
        this.observer = null;
      }
      this.scenes.clear();
    }

    start() {
      if (this.isRunning) return;
      this.isRunning = true;
      this.isPaused = false;
      this.lastTimestamp = performance.now();
      this.rafId = requestAnimationFrame(this._onTick);
    }

    stop() {
      this.isRunning = false;
      if (this.rafId) {
        cancelAnimationFrame(this.rafId);
        this.rafId = null;
      }
    }

    pause() {
      this.isPaused = true;
    }

    resume() {
      if (!this.isPaused) return;
      this.isPaused = false;
      this.lastTimestamp = performance.now();
    }

    // ========================================================================
    // 2. MASTER RAF HEARTBEAT
    // ========================================================================
    _tick(now) {
      if (!this.isRunning) return;

      this.rafId = requestAnimationFrame(this._onTick);

      if (this.isPaused) return;

      // Calculate time delta & clamp between 1ms and 100ms
      const rawDelta = (now - this.lastTimestamp) / 1000;
      this.deltaTime = Math.max(0.001, Math.min(0.1, rawDelta));
      this.lastTimestamp = now;
      this.elapsedTime += this.deltaTime;
      this.frameCount++;

      // Smoothed FPS
      const currentFps = 1 / this.deltaTime;
      this.fps = this.fps * (1 - this._fpsSmoothing) + currentFps * this._fpsSmoothing;

      // --- Update Scroll State ---
      this._updateScroll();

      // --- Update Pointer State ---
      this._updatePointer();

      // --- Dispatch to Registered Scenes ---
      this._dispatchScenes();
    }

    _handleVisibilityChange() {
      if (document.hidden) {
        this.pause();
      } else {
        this.resume();
      }
    }

    // ========================================================================
    // 3. SCROLL HANDLING & SECTION PROGRESS
    // ========================================================================
    _handleScroll() {
      this.scroll.targetY = window.pageYOffset || document.documentElement.scrollTop || 0;
      this.scroll.isScrolling = true;

      if (!('onscrollend' in window)) {
        clearTimeout(this._scrollEndTimer);
        this._scrollEndTimer = setTimeout(this._onScrollEnd, 120);
      }
    }

    _handleScrollEnd() {
      this.scroll.isScrolling = false;
      this.scroll.velocity = 0;
    }

    _updateScroll() {
      const s = this.scroll;
      s.previousY = s.currentY;

      if (this.reducedMotion) {
        s.currentY = s.targetY;
      } else {
        s.currentY = damp(s.currentY, s.targetY, s.damping, this.deltaTime);
      }

      // Compute scroll velocity (px/sec)
      s.velocity = (s.currentY - s.previousY) / this.deltaTime;

      // Direction: 1 = down, -1 = up, 0 = rest
      if (Math.abs(s.velocity) > 0.5) {
        s.direction = s.velocity > 0 ? 1 : -1;
      } else {
        s.direction = 0;
      }

      // Normalized Progress across document (0 to 1)
      s.maxScroll = Math.max(0, this.viewport.documentHeight - this.viewport.height);
      s.progress = s.maxScroll > 0 ? clamp(s.currentY / s.maxScroll, 0, 1) : 0;
    }

    /**
     * Measures and caches element document-relative coordinates.
     * Called on init, scene registration, and batched resize.
     */
    measureElementGeometry(el) {
      if (!el || typeof window === 'undefined') return null;
      const scrollY = window.pageYOffset || document.documentElement.scrollTop || 0;
      const rect = el.getBoundingClientRect();
      const top = rect.top + scrollY;
      const height = rect.height || el.offsetHeight || 0;
      const isSticky = el.classList.contains('act-runway') || el.hasAttribute('data-sticky');
      const geom = {
        top,
        height,
        bottom: top + height,
        isSticky
      };
      this.elementGeometry.set(el, geom);
      return geom;
    }

    refreshAllGeometry() {
      if (typeof window === 'undefined') return;
      this.scenes.forEach((scene) => {
        if (scene.element) {
          this.measureElementGeometry(scene.element);
        }
      });
    }

    /**
     * Calculates sticky-aware normalized progress for pinned story stages.
     * 0.0 = Runway top aligns with viewport top (stage locks into sticky position)
     * 1.0 = Runway has fully scrolled through its pin distance (stage unlocks)
     * Completely framerate-independent, uses smoothed currentY, zero layout thrashing.
     */
    getStickyProgress(target, currentY = null) {
      const el = typeof target === 'string' ? document.querySelector(target) : target;
      if (!el) return 0;

      let geom = this.elementGeometry.get(el);
      if (!geom) {
        geom = this.measureElementGeometry(el);
      }
      if (!geom) return 0;

      const viewH = this.viewport.height;
      const y = currentY !== null ? currentY : this.scroll.currentY;

      const maxScroll = geom.height - viewH;
      if (maxScroll <= 20) {
        // Element is not pinned (e.g. mobile responsive unpinned layout)
        return this.getSectionProgress(el);
      }

      const traveled = y - geom.top;
      return clamp(traveled / maxScroll, 0, 1);
    }

    /**
     * Calculates normalized progress of an element relative to the viewport.
     * 0.0 = Element top enters viewport bottom
     * 0.5 = Element center aligns with viewport center
     * 1.0 = Element bottom exits viewport top
     * Uses cached geometry and smoothed scroll coordinates to avoid layout thrashing.
     */
    getSectionProgress(target, options = {}) {
      const el = typeof target === 'string' ? document.querySelector(target) : target;
      if (!el) return 0;

      let geom = this.elementGeometry.get(el);
      if (!geom) {
        geom = this.measureElementGeometry(el);
      }
      if (!geom) return 0;

      const viewH = this.viewport.height;
      const elH = geom.height;
      const totalDistance = viewH + elH;
      if (totalDistance <= 0) return 0;

      const scrollY = options.useRaw ? (window.pageYOffset || 0) : this.scroll.currentY;
      const rectTop = geom.top - scrollY;
      const traveled = viewH - rectTop;
      let progress = traveled / totalDistance;

      if (options.clamp !== false) {
        progress = clamp(progress, 0, 1);
      }

      return progress;
    }

    // ========================================================================
    // 4. POINTER & TOUCH HANDLING
    // ========================================================================
    _handlePointerMove(e) {
      this.pointer.clientX = e.clientX;
      this.pointer.clientY = e.clientY;
      this.pointer.isInside = true;
      this.pointer.isTouch = e.pointerType === 'touch';

      // Normalized coordinates: -1 to 1 with (0,0) at viewport center
      const halfW = this.viewport.width / 2;
      const halfH = this.viewport.height / 2;
      this.pointer.targetX = halfW > 0 ? (e.clientX - halfW) / halfW : 0;
      this.pointer.targetY = halfH > 0 ? (e.clientY - halfH) / halfH : 0;

      // Normalized coordinates: 0 to 1 with (0,0) at top-left
      this.pointer.normX = this.viewport.width > 0 ? e.clientX / this.viewport.width : 0.5;
      this.pointer.normY = this.viewport.height > 0 ? e.clientY / this.viewport.height : 0.5;
    }

    _handlePointerLeave() {
      this.pointer.isInside = false;
      this.pointer.targetX = 0;
      this.pointer.targetY = 0;
    }

    _handleTouchMove(e) {
      if (e.touches && e.touches.length > 0) {
        const touch = e.touches[0];
        this._handlePointerMove({
          clientX: touch.clientX,
          clientY: touch.clientY,
          pointerType: 'touch'
        });
      }
    }

    _updatePointer() {
      const p = this.pointer;
      p.prevX = p.dampedX;
      p.prevY = p.dampedY;

      if (this.reducedMotion) {
        p.dampedX = p.targetX;
        p.dampedY = p.targetY;
        p.velocityX = 0;
        p.velocityY = 0;
      } else {
        p.dampedX = damp(p.dampedX, p.targetX, p.damping, this.deltaTime);
        p.dampedY = damp(p.dampedY, p.targetY, p.damping, this.deltaTime);
        p.velocityX = (p.dampedX - p.prevX) / this.deltaTime;
        p.velocityY = (p.dampedY - p.prevY) / this.deltaTime;
      }
    }

    // ========================================================================
    // 5. RESIZE & VIEWPORT HANDLING
    // ========================================================================
    _handleResize() {
      // Use single RAF debounce for resize calculation
      if (this._resizeScheduled) return;
      this._resizeScheduled = true;

      requestAnimationFrame(() => {
        this._measureViewport();
        this.refreshAllGeometry();
        this._resizeScheduled = false;

        // Notify scenes
        this.scenes.forEach((scene) => {
          if (typeof scene.onResize === 'function') {
            scene.onResize({
              viewport: this.viewport,
              isMobile: this.isMobile,
              isTablet: this.isTablet,
              isDesktop: this.isDesktop
            });
          }
        });
      });
    }

    _measureViewport() {
      const w = window.innerWidth;
      const h = window.innerHeight;
      this.viewport.width = w;
      this.viewport.height = h;
      this.viewport.dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.viewport.aspectRatio = h > 0 ? w / h : 1.6;
      this.viewport.documentHeight = Math.max(
        document.body.scrollHeight,
        document.documentElement.scrollHeight,
        document.body.offsetHeight,
        document.documentElement.offsetHeight,
        document.body.clientHeight,
        document.documentElement.clientHeight
      );

      this.isMobile = w <= 768;
      this.isTablet = w > 768 && w <= 1024;
      this.isDesktop = w > 1024;
    }

    // ========================================================================
    // 6. SCENE REGISTRATION & DISPATCH
    // ========================================================================
    /**
     * Register a scene controller to receive motion callbacks.
     * @param {string} id Unique identifier for the scene
     * @param {Object} config Scene options:
     *   - element: HTMLElement or CSS selector
     *   - onTick: function({ progress, scroll, pointer, viewport, visibility, deltaTime, elapsed })
     *   - onEnter: function({ entry, engine })
     *   - onLeave: function({ entry, engine })
     *   - onResize: function({ viewport, ... })
     *   - runAlways: boolean (execute onTick even if offscreen)
     *   - damping: number (custom damping override)
     */
    registerScene(id, config = {}) {
      if (!id) throw new Error('[PortfoliAIMotion] registerScene requires an id.');

      const el = typeof config.element === 'string'
        ? document.querySelector(config.element)
        : config.element;

      const isSticky = Boolean(config.isSticky || (el && (el.classList.contains('act-runway') || el.hasAttribute('data-sticky'))));
      const descriptor = {
        id,
        element: el || null,
        onTick: config.onTick || null,
        onEnter: config.onEnter || null,
        onLeave: config.onLeave || null,
        onResize: config.onResize || null,
        runAlways: Boolean(config.runAlways),
        damping: config.damping || 10,
        isSticky,
        isVisible: el ? false : true, // If no element, default visible
        intersectionRatio: 0,
        isPaused: false,
        progress: 0,
        userData: config.userData || {}
      };

      if (el) {
        this.measureElementGeometry(el);
        if (this.observer) {
          el.setAttribute('data-motion-scene', id);
          this.observer.observe(el);
        }
      }

      this.scenes.set(id, descriptor);

      if (this.debug) {
        console.debug(`[PortfoliAIMotion] Registered scene: ${id} (sticky: ${isSticky})`);
      }

      return descriptor;
    }

    unregisterScene(id) {
      if (!this.scenes.has(id)) return false;

      const descriptor = this.scenes.get(id);
      if (descriptor.element && this.observer) {
        this.observer.unobserve(descriptor.element);
      }

      this.scenes.delete(id);
      return true;
    }

    getScene(id) {
      return this.scenes.get(id) || null;
    }

    pauseScene(id) {
      const scene = this.scenes.get(id);
      if (scene) scene.isPaused = true;
    }

    resumeScene(id) {
      const scene = this.scenes.get(id);
      if (scene) scene.isPaused = false;
    }

    _dispatchScenes() {
      if (this.scenes.size === 0) return;

      const context = {
        scroll: this.scroll,
        pointer: this.pointer,
        viewport: this.viewport,
        deltaTime: this.deltaTime,
        elapsedTime: this.elapsedTime,
        fps: this.fps,
        reducedMotion: this.reducedMotion,
        utils: this.utils
      };

      this.scenes.forEach((scene) => {
        if (scene.isPaused) return;

        // Only run tick if scene is visible or configured with runAlways
        if (!scene.isVisible && !scene.runAlways) return;

        // Calculate section-level progress if element exists
        if (scene.element) {
          const geom = this.elementGeometry.get(scene.element);
          if (geom && (geom.isSticky || scene.isSticky)) {
            scene.progress = this.getStickyProgress(scene.element, this.scroll.currentY);
          } else {
            scene.progress = this.getSectionProgress(scene.element);
          }
        } else {
          scene.progress = this.scroll.progress;
        }

        if (typeof scene.onTick === 'function') {
          scene.onTick({
            ...context,
            progress: scene.progress,
            isVisible: scene.isVisible,
            intersectionRatio: scene.intersectionRatio,
            scene
          });
        }
      });
    }

    // ========================================================================
    // 7. COMPOSITOR-FRIENDLY DOM UTILITIES
    // ========================================================================
    setTransform(element, opts = {}) {
      if (!element || !element.style) return;

      const x = opts.x || 0;
      const y = opts.y || 0;
      const z = opts.z || 0;
      const rotX = opts.rotateX || 0;
      const rotY = opts.rotateY || 0;
      const rotZ = opts.rotateZ || opts.rotate || 0;
      const scaleX = opts.scaleX !== undefined ? opts.scaleX : (opts.scale !== undefined ? opts.scale : 1);
      const scaleY = opts.scaleY !== undefined ? opts.scaleY : (opts.scale !== undefined ? opts.scale : 1);
      const scaleZ = opts.scaleZ !== undefined ? opts.scaleZ : 1;

      let transformStr = `translate3d(${typeof x === 'number' ? x + 'px' : x}, ${typeof y === 'number' ? y + 'px' : y}, ${typeof z === 'number' ? z + 'px' : z})`;

      if (rotX) transformStr += ` rotateX(${rotX}deg)`;
      if (rotY) transformStr += ` rotateY(${rotY}deg)`;
      if (rotZ) transformStr += ` rotateZ(${rotZ}deg)`;
      if (scaleX !== 1 || scaleY !== 1 || scaleZ !== 1) {
        transformStr += ` scale3d(${scaleX}, ${scaleY}, ${scaleZ})`;
      }

      element.style.transform = transformStr;
    }

    setOpacity(element, opacity) {
      if (!element || !element.style) return;
      element.style.opacity = Math.max(0, Math.min(1, opacity)).toFixed(3);
    }

    setBlur(element, blurPx) {
      if (!element || !element.style) return;
      element.style.filter = blurPx > 0.1 ? `blur(${blurPx.toFixed(1)}px)` : 'none';
    }

    setCSSVar(element, name, value) {
      const el = element || document.documentElement;
      if (!el || !el.style) return;
      el.style.setProperty(name, value);
    }

    // ========================================================================
    // 8. DIAGNOSTICS & DEBUG
    // ========================================================================
    setDebug(enabled) {
      this.debug = Boolean(enabled);
      return this.debug;
    }

    getDiagnostics() {
      let activeScenesCount = 0;
      this.scenes.forEach((s) => {
        if (s.isVisible && !s.isPaused) activeScenesCount++;
      });

      return {
        fps: Math.round(this.fps),
        frameCount: this.frameCount,
        deltaTimeMs: (this.deltaTime * 1000).toFixed(2),
        isRunning: this.isRunning,
        isPaused: this.isPaused,
        totalScenes: this.scenes.size,
        activeScenes: activeScenesCount,
        reducedMotion: this.reducedMotion,
        scroll: {
          currentY: Math.round(this.scroll.currentY),
          targetY: Math.round(this.scroll.targetY),
          velocity: Math.round(this.scroll.velocity),
          progress: this.scroll.progress.toFixed(3)
        },
        pointer: {
          dampedX: this.pointer.dampedX.toFixed(3),
          dampedY: this.pointer.dampedY.toFixed(3),
          velocityX: Math.round(this.pointer.velocityX),
          isInside: this.pointer.isInside
        },
        viewport: {
          width: this.viewport.width,
          height: this.viewport.height,
          dpr: this.viewport.dpr
        }
      };
    }
  }

  // Singleton Instance
  return new MotionEngine();
});
