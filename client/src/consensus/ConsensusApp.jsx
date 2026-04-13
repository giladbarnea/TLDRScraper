import DOMPurify from 'dompurify'
import { Check, ChevronDown, ChevronUp, Copy, Radar, Send, Sparkles } from 'lucide-react'
import { marked } from 'marked'
import { useMemo, useState } from 'react'
import './consensus.css'

const MODEL_LABELS = {
  claude: 'Claude',
  gpt: 'GPT',
  gemini: 'Gemini',
}

const STARTER_PROMPTS = [
  'Compare Python and Go for backend APIs in 2026 and recommend one for a small team.',
  'Give me the most practical strategy for staying technically sharp while leading engineering managers.',
  'Should I optimize for speed or maintainability in a one-person product? Give a nuanced recommendation.'
]

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button type="button" className="consensus-copy-btn" onClick={handleCopy} title="Copy to clipboard">
      {copied ? <Check size={13} /> : <Copy size={13} />}
    </button>
  )
}

function MarkdownContent({ content, className }) {
  const html = DOMPurify.sanitize(marked.parse(content))
  return <div className={`consensus-md${className ? ` ${className}` : ''}`} dangerouslySetInnerHTML={{ __html: html }} />
}

function MessageBubble({ message }) {
  return (
    <div className={`consensus-message consensus-message-${message.role}`}>
      <div className="consensus-message-meta">
        {message.role === 'user' ? 'You' : (
          <>Consensus <CopyButton text={message.content} /></>
        )}
      </div>
      <div className="consensus-message-body">
        {message.role === 'assistant'
          ? <MarkdownContent content={message.content} />
          : message.content}
      </div>
    </div>
  )
}

function TracePanel({ rounds, reachedConsensus, stopReason, expanded, onToggle }) {
  const statusLabel = reachedConsensus == null
    ? 'No run yet'
    : reachedConsensus
      ? 'Consensus reached'
      : 'Stopped without consensus'
  const lastTurn = rounds.at(-1)?.turn

  return (
    <aside className="consensus-trace">
      <div className="consensus-trace-header">
        <div className="consensus-eyebrow"><Radar size={14} /> Debate trace</div>
        <button type="button" className="consensus-toggle" onClick={onToggle}>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          {expanded ? 'Hide' : 'Show'}
        </button>
      </div>

      <div className="consensus-trace-status">
        <span className={`consensus-pill ${reachedConsensus ? 'is-ok' : ''}`}>{statusLabel}</span>
        {stopReason ? <span className="consensus-subtle">Stop: {stopReason}</span> : null}
      </div>

      {expanded ? (
        rounds.length > 0 ? (
          <div className="consensus-rounds">
            {rounds.map((round) => (
              <details key={round.turn} className="consensus-round" open={round.turn === lastTurn}>
                <summary>Round {round.turn}</summary>
                {Object.entries(round.responses).map(([modelName, response]) => (
                  <div key={modelName} className="consensus-response" data-model={modelName}>
                    <div className="consensus-response-header">
                      <span>{MODEL_LABELS[modelName] || modelName}</span>
                      <CopyButton text={response} />
                    </div>
                    <div className="consensus-response-body">
                      <MarkdownContent content={response} className="consensus-trace-md" />
                    </div>
                  </div>
                ))}
              </details>
            ))}
          </div>
        ) : (
          <div className="consensus-empty-trace">
            <Sparkles size={16} />
            Run a prompt and inspect the hidden model debate.
          </div>
        )
      ) : (
        <p className="consensus-subtle">Open to inspect each internal model round.</p>
      )}
    </aside>
  )
}

export default function ConsensusApp() {
  const [messages, setMessages] = useState([])
  const [nextMessageId, setNextMessageId] = useState(1)
  const [inputValue, setInputValue] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [rounds, setRounds] = useState([])
  const [reachedConsensus, setReachedConsensus] = useState(null)
  const [stopReason, setStopReason] = useState(null)
  const [traceExpanded, setTraceExpanded] = useState(window.innerWidth > 980)

  const canSend = useMemo(() => inputValue.trim().length > 0 && !isRunning, [inputValue, isRunning])

  async function runConsensus(promptText) {
    const userMessage = { id: nextMessageId, role: 'user', content: promptText }
    const nextMessages = [...messages, userMessage]
    setMessages(nextMessages)
    setNextMessageId((value) => value + 1)
    setInputValue('')
    setIsRunning(true)

    try {
      const response = await fetch('/api/consensus/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: nextMessages.map(({ role, content }) => ({ role, content })) })
      })
      const payload = await response.json()
      if (!response.ok || !payload.success) {
        throw new Error(payload.error || `HTTP ${response.status}`)
      }

      const result = payload.result
      setRounds(result.rounds || [])
      setReachedConsensus(result.reached_consensus)
      setStopReason(result.stop_reason)
      setTraceExpanded(true)
      setMessages((current) => [...current, { id: nextMessageId + 1, role: 'assistant', content: result.answer }])
      setNextMessageId((value) => value + 1)
    } catch (error) {
      setRounds([])
      setReachedConsensus(false)
      setStopReason('max_turns')
      setTraceExpanded(true)
      setMessages((current) => [...current, { id: nextMessageId + 1, role: 'assistant', content: `Consensus failed: ${error.message}` }])
      setNextMessageId((value) => value + 1)
    } finally {
      setIsRunning(false)
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    if (!canSend) return
    runConsensus(inputValue.trim())
  }

  return (
    <div className="consensus-root">
      <div className="consensus-shell">
        <header className="consensus-topbar">
          <div>
            <p className="consensus-kicker">Hidden utility</p>
            <h1>Consensus</h1>
            <p className="consensus-subtitle">Three models debate quietly. You get one clean answer.</p>
          </div>
        </header>

        <main className="consensus-grid">
          <section className="consensus-chat">
            {messages.length === 0 ? (
              <div className="consensus-empty">
                <h2>Start with a strong prompt</h2>
                <p>Pick a starter or write your own. The debate trace stays separate on the right.</p>
                <div className="consensus-starters">
                  {STARTER_PROMPTS.map((prompt) => (
                    <button key={prompt} type="button" className="consensus-starter" onClick={() => runConsensus(prompt)}>
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="consensus-thread">
                {messages.map((message) => <MessageBubble key={message.id} message={message} />)}
              </div>
            )}

            <form onSubmit={handleSubmit} className="consensus-composer">
              <textarea
                value={inputValue}
                onChange={(event) => setInputValue(event.target.value)}
                placeholder="Ask anything. Consensus runs on submit."
                rows={3}
                disabled={isRunning}
              />
              <button type="submit" disabled={!canSend}>
                <Send size={16} />
                {isRunning ? 'Running...' : 'Run consensus'}
              </button>
            </form>
          </section>

          <TracePanel
            rounds={rounds}
            reachedConsensus={reachedConsensus}
            stopReason={stopReason}
            expanded={traceExpanded}
            onToggle={() => setTraceExpanded((open) => !open)}
          />
        </main>
      </div>
    </div>
  )
}
