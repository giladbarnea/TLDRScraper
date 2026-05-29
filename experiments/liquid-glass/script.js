/* =============================================================================
   Liquid Glass — behaviour layer with real WebGL refraction.

   Architecture
   ------------
   1. #backdrop (2D canvas):
        – Draws the grey gradient, the "Liquid Glass" headline, and the
          paragraph text in a single Canvas2D pass. This is the page content.
        – Uploaded to GPU as a texture for the lens shader.
   2. #lens (WebGL canvas, full viewport):
        – Fragment shader samples #backdrop with rim-concentrated offsets.
        – Transparent outside the pill silhouette, refracted inside.
   3. .lg-pill (DOM):
        – CSS material (tint, glow, specular, content) stacks on top.
        – Pointer input drives transform-origin, tilt, glow intensity, and
          the shader's press uniform.

   Why this works on mobile where SVG backdrop-filter doesn't:
   WebGL is universally available; only the SVG backdrop-filter route is
   broken on WebKit. Direct texture sampling sidesteps that entirely.
============================================================================= */

(() => {
  "use strict";

  const stage    = document.getElementById("stage");
  const backdrop = document.getElementById("backdrop");
  const lens     = document.getElementById("lens");
  const pill     = document.getElementById("pill");

  const ctx = backdrop.getContext("2d");
  const gl  = lens.getContext("webgl", { alpha: true, premultipliedAlpha: true });
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---------- Sizing --------------------------------------------------------
  const dpr = () => Math.min(window.devicePixelRatio || 1, 2);

  // ==========================================================================
  // 1. Backdrop canvas — gradient + text
  // ==========================================================================
  const drawBackdrop = () => {
    const w = stage.clientWidth;
    const h = stage.clientHeight;
    const r = dpr();
    backdrop.width  = Math.round(w * r);
    backdrop.height = Math.round(h * r);
    backdrop.style.width  = w + "px";
    backdrop.style.height = h + "px";
    ctx.setTransform(r, 0, 0, r, 0, 0);

    // ---- Gradient base. Same painterly grey palette as the reference image,
    //      built from three stacked passes: vertical light→dark + soft top
    //      highlight + bottom-left darken. Background-blend done by hand.
    const g = ctx.createLinearGradient(0, 0, 0, h);
    g.addColorStop(0.00, "#c4c8cc");
    g.addColorStop(0.45, "#a8acb0");
    g.addColorStop(1.00, "#82868a");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);

    // Soft elliptical highlight near the top.
    const hi = ctx.createRadialGradient(w * 0.5, h * 0.3, 0, w * 0.5, h * 0.3, Math.max(w, h) * 0.6);
    hi.addColorStop(0, "rgba(255,255,255,0.32)");
    hi.addColorStop(0.6, "rgba(255,255,255,0)");
    ctx.fillStyle = hi;
    ctx.fillRect(0, 0, w, h);

    // Diagonal darken bottom-left.
    const dk = ctx.createRadialGradient(w * 0.2, h * 1.1, 0, w * 0.2, h * 1.1, Math.max(w, h) * 0.8);
    dk.addColorStop(0, "rgba(0,0,0,0.30)");
    dk.addColorStop(0.55, "rgba(0,0,0,0)");
    ctx.fillStyle = dk;
    ctx.fillRect(0, 0, w, h);

    // ---- Headline ---------------------------------------------------------
    ctx.fillStyle = "rgba(20,20,24,0.86)";
    ctx.textAlign = "center";
    const headlineSize = Math.min(220, Math.max(64, w * 0.16));
    ctx.font = `800 ${headlineSize}px -apple-system, BlinkMacSystemFont, "SF Pro Display", Inter, system-ui, sans-serif`;
    ctx.textBaseline = "alphabetic";
    const headlineY = h * 0.42;
    ctx.fillText("Liquid", w / 2, headlineY);
    ctx.fillText("Glass",  w / 2, headlineY + headlineSize * 0.92);

    // ---- Body paragraph ---------------------------------------------------
    ctx.fillStyle = "rgba(20,20,24,0.6)";
    const bodySize = Math.min(16, Math.max(13, w * 0.024));
    ctx.font = `400 ${bodySize}px -apple-system, BlinkMacSystemFont, "SF Pro Display", Inter, system-ui, sans-serif`;
    const para = "The pill bends what's behind it. Drag your finger across the text and watch the letters distort under the body.";
    wrapText(ctx, para, w / 2, headlineY + headlineSize * 0.92 + bodySize * 4, w * 0.78, bodySize * 1.45);

    // ---- Caption rows -----------------------------------------------------
    ctx.fillStyle = "rgba(20,20,24,0.42)";
    const capSize = Math.min(12, Math.max(10, w * 0.018));
    ctx.font = `500 ${capSize}px ui-monospace, "SF Mono", Menlo, monospace`;
    ctx.letterSpacing = "0.12em";
    const captions = [
      "HIERARCHY · LENSING · MATERIAL",
      "REFRACTION · SPECULAR · GEL",
      "tap · hold · drag · release",
    ];
    let capY = h - capSize * 6;
    captions.forEach((row) => {
      ctx.fillText(row, w / 2, capY);
      capY += capSize * 2;
    });
  };

  /** Naïve word-wrap for canvas text. */
  function wrapText(ctx, text, x, y, maxWidth, lineHeight) {
    const words = text.split(" ");
    let line = "";
    for (let n = 0; n < words.length; n++) {
      const test = line + words[n] + " ";
      if (ctx.measureText(test).width > maxWidth && n > 0) {
        ctx.fillText(line.trim(), x, y);
        line = words[n] + " ";
        y += lineHeight;
      } else {
        line = test;
      }
    }
    ctx.fillText(line.trim(), x, y);
  }

  // ==========================================================================
  // 2. WebGL lens
  // ==========================================================================
  let program = null;
  let uniforms = null;
  let backdropTex = null;

  const initGL = () => {
    if (!gl) return false;

    const vsSrc = document.getElementById("lensVertShader").textContent;
    const fsSrc = document.getElementById("lensFragShader").textContent;

    const compile = (type, src) => {
      const sh = gl.createShader(type);
      gl.shaderSource(sh, src);
      gl.compileShader(sh);
      if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
        console.error("Shader compile error:", gl.getShaderInfoLog(sh));
        return null;
      }
      return sh;
    };
    const vs = compile(gl.VERTEX_SHADER, vsSrc);
    const fs = compile(gl.FRAGMENT_SHADER, fsSrc);
    if (!vs || !fs) return false;

    program = gl.createProgram();
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error("Program link error:", gl.getProgramInfoLog(program));
      return false;
    }
    gl.useProgram(program);

    // Fullscreen quad.
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 1,-1, -1,1, 1,1]), gl.STATIC_DRAW);
    const aPos = gl.getAttribLocation(program, "a_pos");
    gl.enableVertexAttribArray(aPos);
    gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

    uniforms = {
      resolution:     gl.getUniformLocation(program, "iResolution"),
      pill:           gl.getUniformLocation(program, "iPill"),
      backdrop:       gl.getUniformLocation(program, "iBackdrop"),
      time:           gl.getUniformLocation(program, "iTime"),
      press:          gl.getUniformLocation(program, "iPress"),
      pressIntensity: gl.getUniformLocation(program, "iPressIntensity"),
    };

    // Premultiplied-alpha blending so the lens output composites cleanly
    // against the backdrop already drawn below.
    gl.enable(gl.BLEND);
    gl.blendFuncSeparate(gl.ONE, gl.ONE_MINUS_SRC_ALPHA, gl.ONE, gl.ONE_MINUS_SRC_ALPHA);

    // Texture for backdrop. Y is flipped so texture UV (0,0) is top-left,
    // matching how we draw to the 2D canvas.
    backdropTex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, backdropTex);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

    return true;
  };

  /** Reupload backdrop after a resize/redraw. Cheap because it's static. */
  const uploadBackdrop = () => {
    gl.bindTexture(gl.TEXTURE_2D, backdropTex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, backdrop);
  };

  const resizeLens = () => {
    const w = stage.clientWidth;
    const h = stage.clientHeight;
    const r = dpr();
    lens.width  = Math.round(w * r);
    lens.height = Math.round(h * r);
    lens.style.width  = w + "px";
    lens.style.height = h + "px";
    if (gl) gl.viewport(0, 0, lens.width, lens.height);
  };

  // ---------- Pointer state -------------------------------------------------
  let pressIntensityTarget = 0;
  let pressIntensity = 0;
  let pressCss = { x: 0, y: 0 };       // CSS pixels in viewport (for shader)
  let activePointerId = null;

  const setVar = (name, value) => pill.style.setProperty(name, value);

  const updateContact = (event, anchorOrigin) => {
    const rect = pill.getBoundingClientRect();
    const xPct = ((event.clientX - rect.left) / rect.width) * 100;
    const yPct = ((event.clientY - rect.top) / rect.height) * 100;

    // CSS glow tracks finger.
    setVar("--gx", `${xPct}%`);
    setVar("--gy", `${yPct}%`);

    // Press point in viewport coords (CSS pixels), used by the shader.
    pressCss = { x: event.clientX, y: event.clientY };

    if (anchorOrigin) {
      setVar("--press-x", `${xPct}%`);
      setVar("--press-y", `${yPct}%`);
    }

    if (!reducedMotion) {
      const dx = (xPct - 50) / 50;
      const dy = (yPct - 50) / 50;
      const TILT = 6;
      setVar("--tilt-y", `${dx *  TILT}deg`);
      setVar("--tilt-x", `${dy * -TILT}deg`);
    }
  };

  const onDown = (event) => {
    if (activePointerId !== null) return;
    activePointerId = event.pointerId;
    pill.setPointerCapture?.(event.pointerId);
    updateContact(event, true);
    pill.classList.add("is-pressed");
    pressIntensityTarget = 1;
  };
  const onMove = (event) => {
    if (event.pointerId !== activePointerId) return;
    updateContact(event, false);
  };
  const onUp = (event) => {
    if (event.pointerId !== activePointerId) return;
    activePointerId = null;
    pill.classList.remove("is-pressed");
    setVar("--tilt-x", "0deg");
    setVar("--tilt-y", "0deg");
    pressIntensityTarget = 0;
  };

  pill.addEventListener("pointerdown", onDown);
  pill.addEventListener("pointermove", onMove);
  pill.addEventListener("pointerup", onUp);
  pill.addEventListener("pointercancel", onUp);
  pill.addEventListener("pointerleave", onUp);

  // ---------- Render loop --------------------------------------------------
  const start = performance.now();
  const render = () => {
    // Spring the press intensity. Fast rise, slow decay.
    const k = pressIntensityTarget > pressIntensity ? 0.18 : 0.07;
    pressIntensity += (pressIntensityTarget - pressIntensity) * k;
    setVar("--gi", pressIntensity.toFixed(3));

    if (gl && program) {
      const rect = pill.getBoundingClientRect();
      const r = dpr();

      gl.useProgram(program);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, backdropTex);
      gl.uniform1i(uniforms.backdrop, 0);

      gl.uniform2f(uniforms.resolution, lens.width, lens.height);
      gl.uniform4f(
        uniforms.pill,
        rect.left * r,
        rect.top  * r,
        rect.width  * r,
        rect.height * r
      );
      gl.uniform1f(uniforms.time, (performance.now() - start) / 1000);
      gl.uniform2f(uniforms.press, pressCss.x * r, pressCss.y * r);
      gl.uniform1f(uniforms.pressIntensity, pressIntensity);

      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }

    requestAnimationFrame(render);
  };

  // ---------- Boot ---------------------------------------------------------
  const boot = () => {
    drawBackdrop();
    resizeLens();
    if (initGL()) {
      uploadBackdrop();
      requestAnimationFrame(render);
    } else {
      // WebGL unavailable — backdrop canvas already drew the page, the CSS
      // pill still works, you just lose the lens. No further action needed.
      console.warn("WebGL unavailable — pill will render without lensing.");
    }
  };

  let resizeTimer = 0;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      drawBackdrop();
      resizeLens();
      if (gl) uploadBackdrop();
    }, 100);
  });

  // Wait for fonts so the headline rasterises with the right metrics.
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(boot);
  } else {
    boot();
  }
})();
