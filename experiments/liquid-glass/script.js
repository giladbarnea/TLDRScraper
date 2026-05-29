/* =============================================================================
   Liquid Glass — scroll lensing behaviour layer.

   The lens is static. Every dynamic state in the reference (mirror emerging
   squished at a horizon, drifting apart from the upright copy, receding into
   the rim while the upright copy advances to centre, then repeating at the far
   rim) emerges purely from scrolling the backdrop under the fixed refraction.

   Architecture:
     1. #backdrop (2D canvas): dark list rows, redrawn on scroll. Shown directly
        AND uploaded to the GPU as the lens texture.
     2. #lens (WebGL canvas): refracts the backdrop inside the pill silhouette,
        transparent everywhere else.
     3. #pill (DOM): elevation shadow + mic glyph; transparent body.

   Tunables live on window.LG so they can be adjusted live (console / Playwright)
   without re-editing the file.
============================================================================= */

(() => {
  "use strict";

  const backdrop = document.getElementById("backdrop");
  const lens     = document.getElementById("lens");
  const pillEl   = document.getElementById("pill");

  const ctx = backdrop.getContext("2d");
  const gl  = lens.getContext("webgl", { alpha: true, premultipliedAlpha: true, antialias: false });

  // ---- Tunables (CSS px unless noted) -------------------------------------
  const PILL = { maxWidth: 680, widthRatio: 0.92, height: 80, top: 150 };
  const LENS = {
    thickness:  100,   // glass depth — fold magnitude (how deep the mirror dips)
    rimBand:    30,    // width of the rounded rim band each side
    slope:      1.8,   // peak surface slope at mid-band — places the caustic
    innerClear:  3,    // clear ring buffering reflections off the lit rim
    outerRim:    2.0,  // lit specular rim width
    rimLight:    0.6,  // lit rim brightness
    eta:         0.62, // air/glass index ratio (smaller = more bend)
    dampen:      0.10, // attention dampening of refracted content
  };

  const ROW_H   = 132;  // sparse rows so one label traverses a mostly-clear pill
  const FONT_PX = 34;

  const dpr = () => Math.min(window.devicePixelRatio || 1, 2);

  // ---- Content ------------------------------------------------------------
  const LABELS = [
    "Not Connected", "AirPods Pro", "Not Connected", "MacBook Pro",
    "Not Connected", "Magic Mouse", "Not Connected", "Studio Display",
    "Not Connected", "Magic Keyboard", "Not Connected", "iPad Pro",
  ];
  const ROWS = [];
  for (let i = 0; i < 48; i++) ROWS.push(LABELS[i % LABELS.length]);

  let scroll = 0;
  let maxScroll = 0;
  let scrollDirty = true;

  // ---- Pill geometry ------------------------------------------------------
  const pillRect = () => {
    const w = Math.min(PILL.maxWidth, window.innerWidth * PILL.widthRatio);
    return { left: (window.innerWidth - w) / 2, top: PILL.top, width: w, height: PILL.height };
  };

  const layoutPill = () => {
    const r = pillRect();
    pillEl.style.left   = r.left + "px";
    pillEl.style.top    = r.top + "px";
    pillEl.style.width  = r.width + "px";
    pillEl.style.height = r.height + "px";
  };

  // ---- Backdrop -----------------------------------------------------------
  const CONTENT_TOP = 70;

  const drawBackdrop = () => {
    const w = window.innerWidth, h = window.innerHeight, r = dpr();
    backdrop.width  = Math.round(w * r);
    backdrop.height = Math.round(h * r);
    backdrop.style.width  = w + "px";
    backdrop.style.height = h + "px";
    ctx.setTransform(r, 0, 0, r, 0, 0);

    const bg = ctx.createLinearGradient(0, 0, 0, h);
    bg.addColorStop(0, "#101014");
    bg.addColorStop(1, "#050506");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, w, h);

    maxScroll = Math.max(0, CONTENT_TOP + ROWS.length * ROW_H - h + 240);

    ctx.textBaseline = "middle";
    for (let i = 0; i < ROWS.length; i++) {
      const cy = CONTENT_TOP + i * ROW_H + ROW_H / 2 - scroll;
      if (cy < -ROW_H || cy > h + ROW_H) continue;

      ctx.font = `600 ${FONT_PX}px -apple-system, "SF Pro Display", Inter, system-ui, sans-serif`;
      ctx.fillStyle = "rgba(210,210,218,0.92)";
      ctx.textAlign = "left";
      ctx.fillText(ROWS[i], 46, cy);

      ctx.fillStyle = "rgba(150,150,158,0.65)";
      ctx.textAlign = "right";
      ctx.font = `400 ${FONT_PX + 4}px -apple-system, "SF Pro Display", system-ui, sans-serif`;
      ctx.fillText("›", w - 40, cy);

      ctx.strokeStyle = "rgba(255,255,255,0.05)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(46, cy + ROW_H / 2);
      ctx.lineTo(w - 36, cy + ROW_H / 2);
      ctx.stroke();
    }
  };

  // ---- WebGL --------------------------------------------------------------
  let program = null, uniforms = null, tex = null;

  const initGL = () => {
    if (!gl) return false;
    const compile = (type, src) => {
      const s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
        console.error("shader compile:", gl.getShaderInfoLog(s));
        return null;
      }
      return s;
    };
    const vs = compile(gl.VERTEX_SHADER, document.getElementById("vert").textContent);
    const fs = compile(gl.FRAGMENT_SHADER, document.getElementById("frag").textContent);
    if (!vs || !fs) return false;

    program = gl.createProgram();
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error("program link:", gl.getProgramInfoLog(program));
      return false;
    }
    gl.useProgram(program);

    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const aPos = gl.getAttribLocation(program, "a_pos");
    gl.enableVertexAttribArray(aPos);
    gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

    uniforms = {
      res:        gl.getUniformLocation(program, "iResolution"),
      pill:       gl.getUniformLocation(program, "iPill"),
      backdrop:   gl.getUniformLocation(program, "iBackdrop"),
      thickness:  gl.getUniformLocation(program, "iThickness"),
      rimBand:    gl.getUniformLocation(program, "iRimBand"),
      slope:      gl.getUniformLocation(program, "iSlope"),
      innerClear: gl.getUniformLocation(program, "iInnerClear"),
      outerRim:   gl.getUniformLocation(program, "iOuterRim"),
      rimLight:   gl.getUniformLocation(program, "iRimLight"),
      eta:        gl.getUniformLocation(program, "iEta"),
      dampen:     gl.getUniformLocation(program, "iDampen"),
    };

    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);

    tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return true;
  };

  const resizeLens = () => {
    const w = window.innerWidth, h = window.innerHeight, r = dpr();
    lens.width  = Math.round(w * r);
    lens.height = Math.round(h * r);
    lens.style.width  = w + "px";
    lens.style.height = h + "px";
    if (gl) gl.viewport(0, 0, lens.width, lens.height);
  };

  const uploadBackdrop = () => {
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, backdrop);
  };

  const render = () => {
    if (scrollDirty) {
      drawBackdrop();
      if (gl) uploadBackdrop();
      scrollDirty = false;
    }
    if (gl && program) {
      const r = dpr(), pr = pillRect();
      gl.useProgram(program);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.uniform1i(uniforms.backdrop, 0);
      gl.uniform2f(uniforms.res, lens.width, lens.height);
      gl.uniform4f(uniforms.pill, pr.left * r, pr.top * r, pr.width * r, pr.height * r);
      gl.uniform1f(uniforms.thickness, LENS.thickness * r);
      gl.uniform1f(uniforms.rimBand, LENS.rimBand * r);
      gl.uniform1f(uniforms.slope, LENS.slope);
      gl.uniform1f(uniforms.innerClear, LENS.innerClear * r);
      gl.uniform1f(uniforms.outerRim, LENS.outerRim * r);
      gl.uniform1f(uniforms.rimLight, LENS.rimLight);
      gl.uniform1f(uniforms.eta, LENS.eta);
      gl.uniform1f(uniforms.dampen, LENS.dampen);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }
    requestAnimationFrame(render);
  };

  // ---- Scroll input -------------------------------------------------------
  const setScroll = (v) => { scroll = Math.max(0, Math.min(maxScroll, v)); scrollDirty = true; };
  window.addEventListener("wheel", (e) => setScroll(scroll + e.deltaY), { passive: true });

  let dragY = null;
  window.addEventListener("pointerdown", (e) => { dragY = e.clientY; });
  window.addEventListener("pointermove", (e) => {
    if (dragY === null) return;
    setScroll(scroll - (e.clientY - dragY));
    dragY = e.clientY;
  });
  window.addEventListener("pointerup", () => { dragY = null; });

  // Live tuning handle.
  window.LG = {
    LENS, PILL,
    setScroll, redraw: () => { scrollDirty = true; },
    getScroll: () => scroll,
    getMax: () => maxScroll,
  };

  // ---- Boot ---------------------------------------------------------------
  const boot = () => {
    layoutPill();
    resizeLens();
    drawBackdrop();
    if (initGL()) {
      uploadBackdrop();
      requestAnimationFrame(render);
    } else {
      console.warn("WebGL unavailable — backdrop renders without the lens.");
    }
  };

  window.addEventListener("resize", () => { layoutPill(); resizeLens(); scrollDirty = true; });

  if (document.fonts && document.fonts.ready) document.fonts.ready.then(boot);
  else boot();
})();
