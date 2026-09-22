/**
 * PortfoliAI — Act III Dual Identity WebGL Shader (Phase 7E)
 * Creates a dual-layer composition (Raw Student vs. Technical Architect)
 * composited via a custom GLSL fragment shader with localized pointer wave reveal,
 * edge softness, restrained chromatic dispersion, and smooth damping.
 */

(function () {
  'use strict';

  function initIdentityShaderScene() {
    const webglStage = window.PortfoliAIWebGL;
    if (!webglStage) {
      console.warn('[PortfoliAI] WebGLStage not found; skipping Identity Shader Scene.');
      return;
    }

    const placeholder = document.getElementById('identityStage');
    if (!placeholder) return;

    webglStage.init().then(success => {
      if (!success || !webglStage.isSupported) return;

      const THREE = window.THREE;
      const scene = new THREE.Scene();
      const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 10);
      camera.position.z = 1;

      // --- 1. Texture A: Raw Student Resume (Un-enriched Wireframe) ---
      function generateTextureA(name) {
        const c = document.createElement('canvas');
        c.width = 1024;
        c.height = 1024;
        const ctx = c.getContext('2d');

        // Dark monochrome radial background
        const grad = ctx.createRadialGradient(512, 512, 100, 512, 512, 512);
        grad.addColorStop(0, '#141414');
        grad.addColorStop(1, '#080808');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, 1024, 1024);

        // Dashed circular radar ring
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([8, 8]);
        ctx.beginPath();
        ctx.arc(512, 512, 440, 0, Math.PI * 2);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(512, 512, 300, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);

        // Wireframe Avatar Circle
        const isRealCandidate = name && !name.includes('CURRICULUM VITAE');
        const monogramA = isRealCandidate ? name.slice(0, 2).toUpperCase() : 'CV';

        ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 6]);
        ctx.beginPath();
        ctx.arc(512, 360, 90, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.fillStyle = '#888888';
        ctx.font = 'bold 52px monospace';
        ctx.textAlign = 'center';
        ctx.fillText(monogramA, 512, 378);

        // Title: Raw Student Resume
        ctx.fillStyle = '#888888';
        ctx.font = 'bold 36px monospace';
        ctx.fillText('UNSTRUCTURED DOCUMENT ARTIFACT', 512, 510);

        // Status Badge
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
        ctx.strokeRect(342, 545, 340, 42);
        ctx.fillStyle = '#666666';
        ctx.font = '600 20px monospace';
        ctx.fillText('STATUS: PENDING LOCAL SYNTHESIS', 512, 573);

        // Editorial Muted Text
        ctx.fillStyle = '#555555';
        ctx.font = '24px -apple-system, BlinkMacSystemFont, sans-serif';
        ctx.fillText('Raw flat text · Unindexed capabilities', 512, 640);
        ctx.fillText('Static bullet points · Awaiting architectural synthesis', 512, 680);

        ctx.font = '18px monospace';
        ctx.fillStyle = '#444444';
        ctx.fillText('[ SCAN POINTER TO REVEAL PROFESSIONAL IDENTITY ]', 512, 780);

        const tex = new THREE.CanvasTexture(c);
        tex.minFilter = THREE.LinearFilter;
        tex.magFilter = THREE.LinearFilter;
        return tex;
      }

      // --- 2. Texture B: Technical Professional Engine (Monochrome Synthesis) ---
      function generateTextureB(name, headline) {
        const c = document.createElement('canvas');
        c.width = 1024;
        c.height = 1024;
        const ctx = c.getContext('2d');

        // Deep graphite / black background with restrained specular core
        const grad = ctx.createRadialGradient(512, 512, 80, 512, 512, 512);
        grad.addColorStop(0, '#222222');
        grad.addColorStop(0.6, '#111111');
        grad.addColorStop(1, '#060606');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, 1024, 1024);

        // Circuit Grid Lines (Silver Hairlines)
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
        ctx.lineWidth = 1;
        for (let r = 120; r < 500; r += 70) {
          ctx.beginPath();
          ctx.arc(512, 512, r, 0, Math.PI * 2);
          ctx.stroke();
        }
        for (let a = 0; a < Math.PI * 2; a += Math.PI / 6) {
          ctx.beginPath();
          ctx.moveTo(512, 512);
          ctx.lineTo(512 + Math.cos(a) * 480, 512 + Math.sin(a) * 480);
          ctx.stroke();
        }

        // Luminous Monochromatic Avatar Badge
        const isRealCandidate = name && !name.includes('CURRICULUM VITAE');
        const monogramB = isRealCandidate ? name.slice(0, 2).toUpperCase() : 'ID';
        const displayName = isRealCandidate ? name : 'SYNTHESIZED IDENTITY';
        const displayRole = isRealCandidate ? (headline || 'Verified Engineering Profile') : 'ARCHITECTURAL PORTFOLIO SYSTEM';

        const avGrad = ctx.createLinearGradient(420, 270, 604, 450);
        avGrad.addColorStop(0, '#FFFFFF');
        avGrad.addColorStop(1, '#D4D4D8');
        ctx.fillStyle = avGrad;
        ctx.beginPath();
        ctx.arc(512, 360, 90, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = '#000000';
        ctx.font = 'bold 56px -apple-system, BlinkMacSystemFont, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(monogramB, 512, 380);

        // Candidate Name
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 44px -apple-system, BlinkMacSystemFont, sans-serif';
        ctx.fillText(displayName, 512, 505);

        // Role / Title
        ctx.fillStyle = '#D4D4D8';
        ctx.font = '600 24px monospace';
        ctx.fillText(displayRole, 512, 545);

        // Status Badge
        ctx.fillStyle = 'rgba(255, 255, 255, 0.06)';
        ctx.fillRect(312, 580, 400, 44);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(312, 580, 400, 44);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 20px monospace';
        ctx.fillText('STATUS: VERIFIED PROFESSIONAL', 512, 609);

        // Verified Highlights
        ctx.fillStyle = '#D4D4D8';
        ctx.font = '22px -apple-system, sans-serif';
        ctx.fillText('Authentic career capabilities · Verified engineering systems', 512, 675);
        ctx.fillText('Deterministic PostgreSQL storage · Zero-leakage privacy', 512, 715);

        // Telemetry Footer
        ctx.fillStyle = '#A1A1AA';
        ctx.font = '18px monospace';
        ctx.fillText('● SYSTEM VERIFIED · RELATIONAL INTEGRITY', 512, 785);

        const tex = new THREE.CanvasTexture(c);
        tex.minFilter = THREE.LinearFilter;
        tex.magFilter = THREE.LinearFilter;
        return tex;
      }

      const domName = document.querySelector('.artifact-name')?.textContent?.trim() || '';
      const domRole = document.querySelector('.artifact-role')?.textContent?.trim() || '';

      let texA = generateTextureA(domName);
      let texB = generateTextureB(domName, domRole);

      // --- 3. Custom GLSL Shader Material ---
      const vertexShader = `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = vec4(position, 1.0);
        }
      `;

      const fragmentShader = `
        uniform sampler2D uTextureA;
        uniform sampler2D uTextureB;
        uniform vec2 uPointer;
        uniform float uRadius;
        uniform float uSoftness;
        uniform float uTime;
        uniform float uChromatic;
        varying vec2 vUv;

        void main() {
          // Centered circular coordinates
          vec2 delta = vUv - uPointer;
          float dist = length(delta);

          // Subtle harmonic wave disturbance along reveal frontier
          float wave = sin(dist * 34.0 - uTime * 3.0) * 0.010 * smoothstep(uRadius + 0.12, uRadius, dist);
          float perturbedDist = dist + wave;

          // Reveal mask factor (0.0 = Base Student, 1.0 = Revealed Professional)
          float mask = 1.0 - smoothstep(uRadius - uSoftness, uRadius + uSoftness, perturbedDist);

          // Base layer sample
          vec4 colA = texture2D(uTextureA, vUv);

          // Subtle specular dispersion at the wave threshold
          float edgeFactor = smoothstep(uRadius - 0.06, uRadius, perturbedDist) * (1.0 - smoothstep(uRadius, uRadius + 0.06, perturbedDist));
          vec2 chromOffset = normalize(delta + 0.0001) * edgeFactor * (0.008 * uChromatic);

          vec4 colB;
          colB.r = texture2D(uTextureB, vUv + chromOffset).r;
          colB.g = texture2D(uTextureB, vUv).g;
          colB.b = texture2D(uTextureB, vUv - chromOffset).b;
          colB.a = texture2D(uTextureB, vUv).a;

          // Pure silver specular sheen along transition wave (No loud colored glow)
          vec3 edgeGlow = vec3(0.9, 0.9, 0.95) * edgeFactor * 1.4;

          // Final composite
          vec4 finalCol = mix(colA, colB, mask);
          finalCol.rgb += edgeGlow;

          // Circular stencil cutoff matching container
          float circleCut = 1.0 - smoothstep(0.485, 0.5, length(vUv - 0.5));
          gl_FragColor = vec4(finalCol.rgb, finalCol.a * circleCut);
        }
      `;

      const uniforms = {
        uTextureA: { value: texA },
        uTextureB: { value: texB },
        uPointer: { value: new THREE.Vector2(0.5, 0.5) },
        uRadius: { value: 0.35 },
        uSoftness: { value: 0.09 },
        uTime: { value: 0.0 },
        uChromatic: { value: 1.0 }
      };

      const material = new THREE.ShaderMaterial({
        vertexShader,
        fragmentShader,
        uniforms,
        transparent: true,
        depthTest: false,
        depthWrite: false
      });

      const geometry = new THREE.PlaneGeometry(2, 2);
      const quadMesh = new THREE.Mesh(geometry, material);
      scene.add(quadMesh);

      // --- 4. Pointer Physics & Smooth Damping ---
      let targetX = 0.5;
      let targetY = 0.5;
      let currentX = 0.5;
      let currentY = 0.5;
      let localTime = 0;

      function onPointerMove(e) {
        const rect = placeholder.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) return;
        targetX = (e.clientX - rect.left) / rect.width;
        // Invert Y for WebGL UV coordinate convention
        targetY = 1.0 - ((e.clientY - rect.top) / rect.height);
      }

      function onPointerLeave() {
        targetX = 0.5;
        targetY = 0.5;
      }

      placeholder.addEventListener('pointermove', onPointerMove, { passive: true });
      placeholder.addEventListener('pointerleave', onPointerLeave, { passive: true });

      // --- 5. Register with Shared WebGL Stage ---
      webglStage.registerScene('act-3-identity', {
        element: placeholder,
        scene,
        camera,
        onTick: ({ deltaTime, reducedMotion }) => {
          localTime += deltaTime;
          uniforms.uTime.value = localTime;

          if (reducedMotion) {
            uniforms.uPointer.value.set(0.5, 0.5);
            uniforms.uRadius.value = 0.45;
            uniforms.uChromatic.value = 0.0;
            return;
          }

          // Smooth exponential damping toward pointer
          currentX += (targetX - currentX) * 0.12;
          currentY += (targetY - currentY) * 0.12;
          uniforms.uPointer.value.set(currentX, currentY);
          uniforms.uChromatic.value = 1.0;
        },
        dispose: () => {
          placeholder.removeEventListener('pointermove', onPointerMove);
          placeholder.removeEventListener('pointerleave', onPointerLeave);
          geometry.dispose();
          material.dispose();
          if (texA) texA.dispose();
          if (texB) texB.dispose();
        }
      });

      // Listen for resume updates
      window.addEventListener('portfoliai:resume-updated', (e) => {
        if (e.detail && e.detail.name) {
          if (texA) texA.dispose();
          if (texB) texB.dispose();
          texA = generateTextureA(e.detail.name);
          texB = generateTextureB(e.detail.name, e.detail.headline);
          uniforms.uTextureA.value = texA;
          uniforms.uTextureB.value = texB;
        }
      });

      console.info('[PortfoliAI WebGL] Act III Dual Identity Shader Scene loaded and bound.');
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initIdentityShaderScene);
  } else {
    initIdentityShaderScene();
  }
})();
