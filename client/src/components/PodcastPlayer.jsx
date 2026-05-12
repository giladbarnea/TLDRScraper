import { Pause, Play, RotateCcw, RotateCw, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

function PlayerButton({ label, icon, onClick }) {
  const className = 'flex h-11 w-11 items-center justify-center rounded-full bg-white/10 text-white transition-colors hover:bg-white/20'

  return (
    <button type="button" aria-label={label} onClick={onClick} className={className}>
      {icon}
    </button>
  )
}

function PodcastPlayer({ audioUrl, onClose }) {
  const audioRef = useRef(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return undefined

    const markPlaying = () => setIsPlaying(true)
    const markPaused = () => setIsPlaying(false)
    const syncTime = () => setCurrentTime(audio.currentTime)
    const syncDuration = () => setDuration(Number.isFinite(audio.duration) ? audio.duration : 0)
    audio.addEventListener('play', markPlaying)
    audio.addEventListener('pause', markPaused)
    audio.addEventListener('ended', markPaused)
    audio.addEventListener('timeupdate', syncTime)
    audio.addEventListener('loadedmetadata', syncDuration)
    audio.addEventListener('durationchange', syncDuration)

    audio.play().catch(() => {})

    return () => {
      audio.pause()
      audio.removeEventListener('play', markPlaying)
      audio.removeEventListener('pause', markPaused)
      audio.removeEventListener('ended', markPaused)
      audio.removeEventListener('timeupdate', syncTime)
      audio.removeEventListener('loadedmetadata', syncDuration)
      audio.removeEventListener('durationchange', syncDuration)
    }
  }, [])

  function seekToFraction(event) {
    const audio = audioRef.current
    if (!audio || !duration) return
    const rect = event.currentTarget.getBoundingClientRect()
    const fraction = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width))
    audio.currentTime = fraction * duration
  }

  const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0

  function seek(seconds) {
    const audio = audioRef.current
    if (!audio) return
    audio.currentTime = Math.max(0, Math.min(audio.duration || 0, audio.currentTime + seconds))
  }

  function togglePlayback() {
    const audio = audioRef.current
    if (!audio) return
    if (audio.paused) {
      void audio.play()
      return
    }
    audio.pause()
  }

  return (
    <div className="fixed inset-x-0 bottom-0 z-[10000] h-[15vh] min-h-28 border-t border-white/10 bg-slate-950/95 text-white shadow-2xl backdrop-blur-xl">
      <audio ref={audioRef} src={audioUrl} preload="auto">
        <track kind="captions" label="No captions" src="data:text/vtt,WEBVTT" />
      </audio>
      <button
        type="button"
        aria-label="Seek podcast"
        onClick={seekToFraction}
        className="group absolute inset-x-0 top-0 h-2 cursor-pointer bg-transparent"
      >
        <div className="pointer-events-none h-px w-full bg-white/15 group-hover:h-0.5 transition-[height]">
          <div className="h-full bg-white/70" style={{ width: `${progressPercent}%` }} />
        </div>
      </button>
      <button
        type="button"
        aria-label="Close podcast player"
        onClick={onClose}
        className="absolute right-4 top-3 flex h-8 w-8 items-center justify-center rounded-full text-slate-500 transition-colors hover:bg-white/10 hover:text-white"
      >
        <X size={18} />
      </button>
      <div className="flex h-full items-center justify-center gap-7 px-6">
        <PlayerButton label="Back 15 seconds" icon={<RotateCcw size={24} />} onClick={() => seek(-15)} />
        <PlayerButton label={isPlaying ? 'Pause podcast' : 'Play podcast'} icon={isPlaying ? <Pause size={30} /> : <Play size={30} />} onClick={togglePlayback} />
        <PlayerButton label="Forward 10 seconds" icon={<RotateCw size={24} />} onClick={() => seek(10)} />
      </div>
    </div>
  )
}

export default PodcastPlayer
