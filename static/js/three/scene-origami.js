/**
 * PortfoliAI — Act I Origami Paper Resume (Phase 7E)
 * Creates a physical floating paper resume with procedural vertex folding,
 * 4-stage continuous scroll morphing (Flat -> Creased -> Folded -> Data Core),
 * physical lighting, damped pointer tilt, and interactive drop feedback.
 */

(function () {
  'use strict';

  function initOrigamiScene() {
    const webglStage = window.PortfoliAIWebGL;
    if (!webglStage) {
      console.warn('[PortfoliAI] WebGLStage not found; skipping Origami Scene.');
      return;
    }

    const placeholder = document.getElementById('hero3DResume');
    if (!placeholder) return;

    webglStage.init().then(success => {
      if (!success || !webglStage.isSupported) return;

      const THREE = window.THREE;
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 50);
      camera.position.set(0, 0, 6.2);

      // --- 1. Lighting Setup (Cinematic paper studio) ---
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
      scene.add(ambientLight);

      // Key light: directional crisp white from upper-right
      const keyLight = new THREE.DirectionalLight(0xffffff, 1.15);
      keyLight.position.set(3, 4, 5);
      scene.add(keyLight);

      // Rim light: soft silver rim radiance from lower-left (replaces violet)
      const rimLight = new THREE.DirectionalLight(0xe4e4e7, 0.75);
      rimLight.position.set(-4, -3, 2);
      scene.add(rimLight);

      // Internal Core Light (pure white specular sheen during data core collapse)
      const coreLight = new THREE.PointLight(0xffffff, 0, 4);
      coreLight.position.set(0, 0, 0);
      scene.add(coreLight);

      // --- 2. Dynamic Canvas Texture Generation (Tactile Resume) ---
      function generatePaperTexture(candidateName, headline) {
        const texCanvas = document.createElement('canvas');
        texCanvas.width = 1024;
        texCanvas.height = 1366;
        const ctx = texCanvas.getContext('2d');

        // Background: tactile architectural paper card (#F8F8F6 off-white paper)
        ctx.fillStyle = '#F8F8F6';
        ctx.fillRect(0, 0, 1024, 1366);

        // Subtle paper fiber grain
        ctx.fillStyle = 'rgba(0, 0, 0, 0.02)';
        for (let i = 0; i < 20000; i++) {
          const gx = Math.random() * 1024;
          const gy = Math.random() * 1366;
          ctx.fillRect(gx, gy, 1.5, 1.5);
        }

        // Architectural hairline grid lines
        ctx.strokeStyle = 'rgba(0, 0, 0, 0.04)';
        ctx.lineWidth = 1;
        for (let x = 60; x < 1024; x += 80) {
          ctx.beginPath();
          ctx.moveTo(x, 0);
          ctx.lineTo(x, 1366);
          ctx.stroke();
        }
        for (let y = 60; y < 1366; y += 80) {
          ctx.beginPath();
          ctx.moveTo(0, y);
          ctx.lineTo(1024, y);
          ctx.stroke();
        }

        // Architectural Outer Frame
        ctx.strokeStyle = 'rgba(0, 0, 0, 0.15)';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(40, 40, 944, 1286);

        // Inner Hairline Frame
        ctx.strokeStyle = 'rgba(0, 0, 0, 0.06)';
        ctx.lineWidth = 1;
        ctx.strokeRect(46, 46, 932, 1274);

        // Avatar monogram
        const isRealCandidate = candidateName && !candidateName.includes('CURRICULUM VITAE');
        const displayName = isRealCandidate ? candidateName : 'CURRICULUM VITAE';
        const displayRole = isRealCandidate ? (headline || 'Software Engineer') : 'UNSTRUCTURED DOCUMENT // ARTIFACT';
        const monogram = isRealCandidate ? displayName.slice(0, 2).toUpperCase() : 'CV';

        ctx.fillStyle = '#111111';
        ctx.fillRect(70, 70, 90, 90);
        ctx.fillStyle = '#F8F8F6';
        ctx.font = 'bold 36px monospace';
        ctx.fillText(monogram, 95, 128);

        // Candidate Name
        ctx.fillStyle = '#111111';
        ctx.font = 'bold 40px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        ctx.fillText(displayName, 185, 110);

        // Headline
        ctx.fillStyle = '#555555';
        ctx.font = '600 22px monospace';
        ctx.fillText(displayRole, 185, 145);

        // Divider
        ctx.strokeStyle = 'rgba(0, 0, 0, 0.12)';
        ctx.beginPath();
        ctx.moveTo(70, 185);
        ctx.lineTo(954, 185);
        ctx.stroke();

        // Detected Entities Section
        ctx.fillStyle = '#222222';
        ctx.font = '700 20px monospace';
        ctx.fillText('DETECTED ENTITIES // SYSTEM METRICS', 70, 230);

        // Extract real skills from DOM if present
        const domPills = Array.from(document.querySelectorAll('.artifact-pills .artifact-pill'))
          .map(p => p.textContent.trim())
          .filter(Boolean);
        const skills = domPills.length > 0 ? domPills.slice(0, 6) : ['[ IDENTITY ]', '[ SUMMARY ]', '[ CAPABILITIES ]', '[ CHRONOLOGY ]'];

        let sx = 70;
        let sy = 265;
        skills.forEach(skill => {
          ctx.font = '500 18px monospace';
          const w = ctx.measureText(skill).width + 32;
          if (sx + w > 940) {
            sx = 70;
            sy += 50;
          }
          ctx.fillStyle = '#ECECE9';
          ctx.fillRect(sx, sy, w, 36);
          ctx.strokeStyle = '#D8D8D5';
          ctx.strokeRect(sx, sy, w, 36);
          ctx.fillStyle = '#111111';
          ctx.fillText(skill, sx + 16, sy + 25);
          sx += w + 12;
        });

        // Experience Section
        sy += 90;
        ctx.fillStyle = '#222222';
        ctx.font = '700 20px monospace';
        ctx.fillText('EXPERIENCE // PRODUCTION DEPLOYMENTS', 70, sy);
        sy += 38;

        const domExp = document.querySelector('.decomp-track-exp div[style*="color:var(--imm-text-secondary)"]')?.textContent?.trim() || '';
        const isRealExp = domExp && !domExp.includes('CHRONOLOGICAL DECOMPOSITION');

        ctx.fillStyle = '#111111';
        ctx.font = 'bold 24px -apple-system, sans-serif';
        if (isRealExp) {
          ctx.fillText(domExp.slice(0, 48), 70, sy);
          sy += 30;
          ctx.fillStyle = '#555555';
          ctx.font = '20px -apple-system, sans-serif';
          ctx.fillText('• Verified career milestone from student profile record.', 70, sy);
        } else {
          ctx.fillText('CHRONOLOGICAL MILESTONES & CAPABILITIES', 70, sy);
          sy += 30;
          ctx.fillStyle = '#555555';
          ctx.font = '20px -apple-system, sans-serif';
          ctx.fillText('• Structural extraction of career history & engineering scope.', 70, sy);
          sy += 28;
          ctx.fillText('• Sourced directly from local database records upon ingestion.', 70, sy);
        }

        // Verification Footer
        ctx.strokeStyle = 'rgba(0, 0, 0, 0.12)';
        ctx.beginPath();
        ctx.moveTo(70, 1240);
        ctx.lineTo(954, 1240);
        ctx.stroke();

        ctx.fillStyle = '#555555';
        ctx.font = '18px monospace';
        ctx.fillText('01 // ID: RESUME_ARTIFACT', 70, 1275);
        ctx.fillStyle = '#111111';
        ctx.fillText('● ZERO-LEAKAGE LOCAL ENGINE', 670, 1275);

        const tex = new THREE.CanvasTexture(texCanvas);
        tex.anisotropy = 4;
        return tex;
      }

      // Initial candidate name from DOM if available
      const domName = document.querySelector('.artifact-name')?.textContent?.trim() || '';
      const domRole = document.querySelector('.artifact-role')?.textContent?.trim() || '';
      let paperTexture = generatePaperTexture(domName, domRole);

      // --- 3. Paper Mesh Construction (Dense Plane for Folding) ---
      const segmentsX = 40;
      const segmentsY = 48;
      const paperWidth = 3.2;
      const paperHeight = 4.27;
      const geometry = new THREE.PlaneGeometry(paperWidth, paperHeight, segmentsX, segmentsY);

      // Cache flat baseline coordinates
      const posAttr = geometry.attributes.position;
      const vertexCount = posAttr.count;
      const origPositions = new Float32Array(posAttr.array);

      const material = new THREE.MeshStandardMaterial({
        map: paperTexture,
        roughness: 0.85,
        metalness: 0.05,
        bumpScale: 0.015,
        side: THREE.DoubleSide,
        emissive: 0xffffff,
        emissiveIntensity: 0
      });

      const paperMesh = new THREE.Mesh(geometry, material);
      const origamiGroup = new THREE.Group();
      origamiGroup.add(paperMesh);
      scene.add(origamiGroup);

      // --- 4. Procedural Continuous Fold / Morph Engine ---
      let currentProgress = 0;
      let lastMorphProgress = -1;
      let isDropActive = false;
      let dropGlow = 0;

      function updatePaperMorph(progress, time, reducedMotion) {
        if (reducedMotion) {
          // Flat rest state for accessibility
          posAttr.array.set(origPositions);
          posAttr.needsUpdate = true;
          geometry.computeVertexNormals();
          coreLight.intensity = 0;
          if (material) material.color.setRGB(1, 1, 1);
          return;
        }

        // Optimization: threshold vertex recalculation if stationary
        const progressDelta = Math.abs(progress - lastMorphProgress);
        if (progressDelta < 0.0006 && !isDropActive) {
          return;
        }
        lastMorphProgress = progress;

        const positions = posAttr.array;

        // Stage 1: Initial Micro-creases (0.0 to 0.30)
        const t1 = Math.min(Math.max(progress / 0.30, 0), 1);
        // Stage 2: Strong Polyhedral Origami Fold (0.30 to 0.65)
        const t2 = Math.min(Math.max((progress - 0.30) / 0.35, 0), 1);
        // Stage 3: Compact Paper Data Core (0.65 to 0.85)
        const t3 = Math.min(Math.max((progress - 0.65) / 0.20, 0), 1);

        // Core light shines as paper collapses into data core
        coreLight.intensity = t3 * 2.5;

        // Fold color shift: off-white paper (1.0) -> architectural gray -> deep graphite (0.28)
        if (material) {
          const shade = 1.0 - (t2 * 0.35 + t3 * 0.37);
          material.color.setRGB(shade, shade, shade);
        }

        for (let i = 0; i < vertexCount; i++) {
          const i3 = i * 3;
          const ox = origPositions[i3];
          const oy = origPositions[i3 + 1];
          const oz = origPositions[i3 + 2];

          // Micro fiber undulation
          const fiberNoise = Math.sin(ox * 4.5 + time * 0.4) * Math.cos(oy * 3.8) * 0.02;

          // Stage 1: Mountain & Valley crease lines
          const creaseHoriz = Math.sin((oy / 2.1) * Math.PI * 3.0) * 0.28 * t1;
          const creaseDiag = Math.sin(((ox + oy) / 1.6) * Math.PI * 2.0) * 0.22 * t1;
          let x = ox * (1.0 - 0.12 * t1);
          let y = oy * (1.0 - 0.14 * t1);
          let z = oz + fiberNoise + creaseHoriz + creaseDiag;

          // Stage 2: Geometric Flap Compression
          if (t2 > 0) {
            const angle = Math.atan2(y, x);
            const dist = Math.sqrt(x * x + y * y);
            const foldFacet = Math.sin(angle * 4.0) * (0.45 + dist * 0.35) * t2;

            x = x * (1.0 - 0.48 * t2);
            y = y * (1.0 - 0.48 * t2);
            z = z + foldFacet;
          }

          // Stage 3: Compact Faceted Paper Ball / Data Core
          if (t3 > 0) {
            const len = Math.sqrt(x * x + y * y + z * z) || 1;
            const coreRadius = 0.72 + (Math.sin(ox * 8.0) * Math.cos(oy * 8.0)) * 0.12;
            const targetX = (x / len) * coreRadius;
            const targetY = (y / len) * coreRadius;
            const targetZ = (z / len) * coreRadius;

            x = x * (1.0 - t3) + targetX * t3;
            y = y * (1.0 - t3) + targetY * t3;
            z = z * (1.0 - t3) + targetZ * t3;
          }

          positions[i3] = x;
          positions[i3 + 1] = y;
          positions[i3 + 2] = z;
        }

        posAttr.needsUpdate = true;
        geometry.computeVertexNormals();
      }

      // --- 5. Register with Shared WebGL Stage ---
      let localTime = 0;
      webglStage.registerScene('act-1-origami', {
        element: placeholder,
        scene,
        camera,
        onTick: ({ progress, pointer, deltaTime, reducedMotion, egressFade }) => {
          localTime += deltaTime;
          currentProgress = progress;

          // Egress bleed prevention: fade material and light smoothly
          const fade = egressFade !== undefined ? egressFade : 1.0;
          material.transparent = true;
          material.opacity = fade;
          coreLight.intensity = coreLight.intensity * fade;

          // Continuous camera dolly: tracks forward as paper folds into data core
          if (!reducedMotion) {
            const targetCamZ = 6.2 - progress * 1.1;
            camera.position.z += (targetCamZ - camera.position.z) * 0.12;
          } else {
            camera.position.z = 6.2;
          }

          // Damped pointer tilt & dynamic core spin
          if (!reducedMotion) {
            const targetRotX = (pointer.dampedY || 0) * -0.22;
            const targetRotY = (pointer.dampedX || 0) * 0.28;
            // Add subtle axial spin as origami condenses into data core
            const coreSpin = (progress > 0.60) ? (progress - 0.60) / 0.40 : 0;
            origamiGroup.rotation.x = targetRotX;
            origamiGroup.rotation.y = targetRotY + (localTime * coreSpin * 0.6);

            // Subtle continuous floating breathing
            origamiGroup.position.y = Math.sin(localTime * 1.5) * 0.06;
          } else {
            origamiGroup.rotation.set(0, 0, 0);
            origamiGroup.position.set(0, 0, 0);
          }

          // Drop interaction glow decay
          const targetGlow = isDropActive ? 0.65 : 0.0;
          dropGlow += (targetGlow - dropGlow) * 0.1;
          material.emissiveIntensity = dropGlow * fade;

          // Vertex morphing
          updatePaperMorph(progress, localTime, reducedMotion);
        },
        dispose: () => {
          geometry.dispose();
          material.dispose();
          if (paperTexture) paperTexture.dispose();
        }
      });

      // --- 6. Drop & Drag Reactivity ---
      ['dragenter', 'dragover'].forEach(evt => {
        placeholder.addEventListener(evt, (e) => {
          e.preventDefault();
          e.stopPropagation();
          isDropActive = true;
          placeholder.classList.add('drop-active');
        });
      });

      ['dragleave', 'drop'].forEach(evt => {
        placeholder.addEventListener(evt, (e) => {
          e.preventDefault();
          e.stopPropagation();
          isDropActive = false;
          placeholder.classList.remove('drop-active');
        });
      });

      // Listen for custom resume data update event
      window.addEventListener('portfoliai:resume-updated', (e) => {
        if (e.detail && e.detail.name) {
          if (paperTexture) paperTexture.dispose();
          paperTexture = generatePaperTexture(e.detail.name, e.detail.headline);
          material.map = paperTexture;
          material.needsUpdate = true;
        }
      });

      console.info('[PortfoliAI WebGL] Act I Origami Scene loaded and bound.');
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initOrigamiScene);
  } else {
    initOrigamiScene();
  }
})();
