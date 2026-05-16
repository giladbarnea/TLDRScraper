import { useEffect, useRef } from 'react'

const MAX_LIGHTS = 4
const PRESS_DURATION_MS = 520
const PEAK_INTENSITY = 0.45

const VERTEX_SOURCE = `
attribute vec2 a_position;
varying vec2 v_uv;
void main() {
  v_uv = a_position * 0.5 + 0.5;
  gl_Position = vec4(a_position, 0.0, 1.0);
}`

const FRAGMENT_SOURCE = `
precision mediump float;
varying vec2 v_uv;
uniform vec2 u_aspect;
uniform vec3 u_lights[${MAX_LIGHTS}];
uniform float u_radius[${MAX_LIGHTS}];
void main() {
  float a = 0.0;
  for (int i = 0; i < ${MAX_LIGHTS}; i++) {
    vec2 delta = (v_uv - u_lights[i].xy) * u_aspect;
    float distance = length(delta);
    float glow = smoothstep(u_radius[i], 0.0, distance) * u_lights[i].z;
    a = max(a, glow);
  }
  gl_FragColor = vec4(1.0, 0.97, 0.9, a);
}`

function compileProgram(gl) {
  const compile = (type, source) => {
    const shader = gl.createShader(type)
    if (!shader) throw new Error(`LiquidGlassTouchLight createShader failed for type ${type}`)
    gl.shaderSource(shader, source)
    gl.compileShader(shader)
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const log = gl.getShaderInfoLog(shader)
      gl.deleteShader(shader)
      throw new Error(`LiquidGlassTouchLight shader compile failed: ${log}`)
    }
    return shader
  }
  const vertexShader = compile(gl.VERTEX_SHADER, VERTEX_SOURCE)
  const fragmentShader = compile(gl.FRAGMENT_SHADER, FRAGMENT_SOURCE)
  const program = gl.createProgram()
  if (!program) throw new Error('LiquidGlassTouchLight createProgram failed')
  gl.attachShader(program, vertexShader)
  gl.attachShader(program, fragmentShader)
  gl.linkProgram(program)
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const log = gl.getProgramInfoLog(program)
    gl.deleteProgram(program)
    throw new Error(`LiquidGlassTouchLight program link failed: ${log}`)
  }
  // biome-ignore lint/correctness/useHookAtTopLevel: WebGL API, not a React hook
  gl.useProgram(program)
  return program
}

function shouldDisableEnhancement() {
  const match = window.matchMedia
  if (!match) return false
  return (
    match('(prefers-reduced-motion: reduce)').matches ||
    match('(prefers-reduced-transparency: reduce)').matches
  )
}

function intensityAt(progress) {
  const riseEnd = 0.18
  if (progress < riseEnd) return (progress / riseEnd) * PEAK_INTENSITY
  const decayProgress = (progress - riseEnd) / (1 - riseEnd)
  return PEAK_INTENSITY * (1 - decayProgress)
}

export default function LiquidGlassTouchLight() {
  const canvasRef = useRef(null)

  useEffect(() => {
    if (shouldDisableEnhancement()) return
    const canvas = canvasRef.current
    const parent = canvas?.parentElement
    if (!canvas || !parent) return

    const gl = canvas.getContext('webgl', { alpha: true, premultipliedAlpha: true, antialias: false })
    console.log('[LiquidGlassTouchLight] webgl context', { supported: Boolean(gl) })
    if (!gl) return

    let program
    try {
      program = compileProgram(gl)
      console.log('[LiquidGlassTouchLight] shader program ready')
    } catch (error) {
      console.warn('[LiquidGlassTouchLight] shader setup failed', error)
      return
    }

    const positionBuffer = gl.createBuffer()
    if (!positionBuffer) {
      console.warn('[LiquidGlassTouchLight] createBuffer failed')
      return
    }
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer)
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW)
    const positionLocation = gl.getAttribLocation(program, 'a_position')
    gl.enableVertexAttribArray(positionLocation)
    gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0)

    const aspectLocation = gl.getUniformLocation(program, 'u_aspect')
    const lightsLocation = gl.getUniformLocation(program, 'u_lights')
    const radiusLocation = gl.getUniformLocation(program, 'u_radius')
    if (!aspectLocation || !lightsLocation || !radiusLocation) {
      console.warn('[LiquidGlassTouchLight] uniform lookup failed', {
        aspectLocation: Boolean(aspectLocation),
        lightsLocation: Boolean(lightsLocation),
        radiusLocation: Boolean(radiusLocation),
      })
      return
    }

    gl.enable(gl.BLEND)
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA)

    const lightsBuffer = new Float32Array(MAX_LIGHTS * 3)
    const radiusBuffer = new Float32Array(MAX_LIGHTS)
    const activeLights = []
    let animationFrameId = null
    let aspect = [1, 1]

    const syncSize = () => {
      const rect = parent.getBoundingClientRect()
      const devicePixelRatio = window.devicePixelRatio || 1
      const widthPx = Math.max(1, Math.round(rect.width * devicePixelRatio))
      const heightPx = Math.max(1, Math.round(rect.height * devicePixelRatio))
      if (canvas.width !== widthPx) canvas.width = widthPx
      if (canvas.height !== heightPx) canvas.height = heightPx
      gl.viewport(0, 0, widthPx, heightPx)
      const minDimension = Math.min(rect.width, rect.height) || 1
      aspect = [rect.width / minDimension, rect.height / minDimension]
    }
    syncSize()

    const resizeObserver = new ResizeObserver(syncSize)
    resizeObserver.observe(parent)

    const drawFrame = () => {
      animationFrameId = null
      const now = performance.now()
      for (let i = activeLights.length - 1; i >= 0; i--) {
        if (now - activeLights[i].startedAt > PRESS_DURATION_MS) activeLights.splice(i, 1)
      }

      gl.clearColor(0, 0, 0, 0)
      gl.clear(gl.COLOR_BUFFER_BIT)

      lightsBuffer.fill(0)
      radiusBuffer.fill(0.0001)

      if (activeLights.length === 0) return

      const limit = Math.min(activeLights.length, MAX_LIGHTS)
      for (let i = 0; i < limit; i++) {
        const light = activeLights[i]
        const progress = (now - light.startedAt) / PRESS_DURATION_MS
        const intensity = intensityAt(progress)
        const radiusInMinDim = 0.1 + 4.5 * progress
        lightsBuffer[i * 3 + 0] = light.u
        lightsBuffer[i * 3 + 1] = 1 - light.v
        lightsBuffer[i * 3 + 2] = Math.max(0, intensity)
        radiusBuffer[i] = Math.max(0.0001, radiusInMinDim)
      }

      gl.uniform2f(aspectLocation, aspect[0], aspect[1])
      gl.uniform3fv(lightsLocation, lightsBuffer)
      gl.uniform1fv(radiusLocation, radiusBuffer)
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4)

      animationFrameId = requestAnimationFrame(drawFrame)
    }

    const handlePointerDown = (event) => {
      const rect = parent.getBoundingClientRect()
      const u = (event.clientX - rect.left) / rect.width
      const v = (event.clientY - rect.top) / rect.height
      console.log('[LiquidGlassTouchLight] pointerdown', {
        x: event.clientX,
        y: event.clientY,
        u,
        v,
        width: rect.width,
        height: rect.height,
      })
      if (u < 0 || u > 1 || v < 0 || v > 1) return
      activeLights.push({ u, v, startedAt: performance.now() })
      if (activeLights.length > MAX_LIGHTS) activeLights.shift()
      if (animationFrameId == null) animationFrameId = requestAnimationFrame(drawFrame)
    }

    parent.addEventListener('pointerdown', handlePointerDown)

    return () => {
      if (animationFrameId != null) cancelAnimationFrame(animationFrameId)
      parent.removeEventListener('pointerdown', handlePointerDown)
      resizeObserver.disconnect()
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none absolute inset-0"
      style={{ borderRadius: 'inherit', zIndex: 0 }}
    />
  )
}
