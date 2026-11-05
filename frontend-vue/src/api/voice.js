// Mic capture encoded as mono 16 kHz 16-bit WAV — the exact format Meta's
// Muse Voice Transcribe (`asr/transcribe`) accepts. No server-side ffmpeg,
// no key in the browser: the blob goes to POST /practice/transcribe/ and
// the transcript travels the identical grading path as typed text.
//
// Usage: const rec = await startRecording(); … const wav = await rec.stop()
// Requires a secure context (localhost or HTTPS) for getUserMedia.
export const VOICE_SUPPORTED =
  typeof window !== 'undefined' &&
  !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia) &&
  !!(window.AudioContext || window.webkitAudioContext)

function encodeWav(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const v = new DataView(buffer)
  const writeStr = (off, s) => {
    for (let i = 0; i < s.length; i++) v.setUint8(off + i, s.charCodeAt(i))
  }
  writeStr(0, 'RIFF')
  v.setUint32(4, 36 + samples.length * 2, true)
  writeStr(8, 'WAVE')
  writeStr(12, 'fmt ')
  v.setUint32(16, 16, true)
  v.setUint16(20, 1, true)
  v.setUint16(22, 1, true)
  v.setUint32(24, sampleRate, true)
  v.setUint32(28, sampleRate * 2, true)
  v.setUint16(32, 2, true)
  v.setUint16(34, 16, true)
  writeStr(36, 'data')
  v.setUint32(40, samples.length * 2, true)
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true)
  }
  return new Blob([buffer], { type: 'audio/wav' })
}

function downsample(chunks, fromRate, toRate) {
  const total = chunks.reduce((n, c) => n + c.length, 0)
  const flat = new Float32Array(total)
  let off = 0
  for (const c of chunks) {
    flat.set(c, off)
    off += c.length
  }
  if (fromRate === toRate) return flat
  const ratio = fromRate / toRate
  const outLen = Math.floor(total / ratio)
  const out = new Float32Array(outLen)
  for (let i = 0; i < outLen; i++) out[i] = flat[Math.floor(i * ratio)]
  return out
}

export async function startRecording() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  const Ctx = window.AudioContext || window.webkitAudioContext
  const ctx = new Ctx()
  const src = ctx.createMediaStreamSource(stream)
  const proc = ctx.createScriptProcessor(4096, 1, 1)
  const chunks = []
  proc.onaudioprocess = (e) => {
    chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)))
  }
  // Route through a zero-gain node: keeps onaudioprocess firing with no feedback.
  const mute = ctx.createGain()
  mute.gain.value = 0
  src.connect(proc)
  proc.connect(mute)
  mute.connect(ctx.destination)
  let stopped = false
  return {
    async stop() {
      if (stopped) return null
      stopped = true
      src.disconnect()
      proc.disconnect()
      mute.disconnect()
      const wav = encodeWav(downsample(chunks, ctx.sampleRate, 16000), 16000)
      stream.getTracks().forEach((t) => t.stop())
      await ctx.close()
      return wav
    },
  }
}
