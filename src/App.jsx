import { useEffect, useRef, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || ''

const FALLBACK_PAPERS = [
  {
    code: 'DA',
    name: 'Data Science & Artificial Intelligence',
    subjects: [
      'Probability & Stats',
      'Linear Algebra',
      'Calculus & Optimization',
      'Programming/DSA',
      'Database Management & Warehousing',
      'Machine Learning',
      'Artificial Intelligence',
    ],
    total: 0,
  },
]

const LANGUAGES = ['English', 'Telugu', 'Hindi']
const LANG_LABELS = { English: 'English', Telugu: 'తెలుగు', Hindi: 'हिन्दी' }

const EXAMPLES = [
  {
    label: 'English · Binomial',
    language: 'English',
    paper: 'DA',
    subject: 'Probability & Stats',
    question:
      'X ~ Binomial(12, 1/3). Find E[X], Var(X), and the most probable value of X.',
  },
  {
    label: 'తెలుగు · Normal distribution',
    language: 'Telugu',
    paper: 'DA',
    subject: 'Probability & Stats',
    question:
      'Normal distribution lo Z-score ante enti? X ~ N(10, 4) aithe P(X > 12) ela find chestaru?',
  },
  {
    label: 'हिन्दी · Mean / Median / Mode',
    language: 'Hindi',
    paper: 'DA',
    subject: 'Probability & Stats',
    question:
      'Mean, median aur mode mein kya antar hai? Data 7, 3, 9, 3, 12, 5 ka mean, median aur mode nikalo.',
  },
  {
    label: 'English · Eigenvalues',
    language: 'English',
    paper: 'DA',
    subject: 'Linear Algebra',
    question: 'Find the eigenvalues of the matrix [[2, 1], [1, 2]].',
  },
  {
    label: 'English · 3NF vs BCNF',
    language: 'English',
    paper: 'DA',
    subject: 'Database Management & Warehousing',
    question: 'What is 3NF, and how is it different from BCNF?',
  },
  {
    label: 'English · Bias–variance',
    language: 'English',
    paper: 'DA',
    subject: 'Machine Learning',
    question:
      "What is the bias-variance tradeoff? Why can't we minimise both at once?",
  },
  {
    label: 'English · A* search',
    language: 'English',
    paper: 'DA',
    subject: 'Artificial Intelligence',
    question:
      'How does A* search work, and when is it guaranteed to find the optimal path?',
  },
  {
    label: 'English · Carnot engine',
    language: 'English',
    paper: 'ME',
    subject: 'Thermodynamics',
    question:
      'A Carnot engine works between 600 K and 300 K. What is its maximum efficiency?',
  },
  {
    label: 'English · Quicksort worst case',
    language: 'English',
    paper: 'CS',
    subject: 'Algorithms',
    question:
      'What is the worst-case time complexity of quicksort, and when does it happen?',
  },
]

const MODE_LABELS = {
  bharatcode: 'Live · BharatCode API',
  adaption: 'Live · Adaption-tuned model',
  'offline-kb': 'Offline · from the knowledge base',
  'error-fallback-kb': 'API failed · offline notes shown',
}

const ENGINES = ['bharatcode', 'adaption']
const ENGINE_LABELS = {
  bharatcode: 'BharatCode Qwen',
  adaption: 'Adaption-tuned',
}

const HISTORY_KEY = 'doubtsahayak-history'

function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
  } catch {
    return []
  }
}

function saveHistory(entry) {
  const prev = loadHistory().filter(
    (h) =>
      h.question !== entry.question ||
      h.subject !== entry.subject ||
      h.paper !== entry.paper,
  )
  const next = [entry, ...prev].slice(0, 20)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(next))
  return next
}

function renderAnswer(text) {
  // Minimal markdown: **bold** + line breaks, no dependency.
  return text.split('\n').map((line, i) => {
    const parts = line.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
      part.startsWith('**') && part.endsWith('**') ? (
        <strong key={j}>{part.slice(2, -2)}</strong>
      ) : (
        part
      ),
    )
    return (
      <p key={i} className={line.trim() === '' ? 'spacer' : ''}>
        {parts}
      </p>
    )
  })
}

function groundingBadge(result) {
  switch (result.grounding_source) {
    case 'drill-notes':
      return <span className="grounded yes">✓ From your GATE DA notes</span>
    case 'reference':
      return (
        <span className="grounded no">
          ⚠ Standard reference — verify against your notes
        </span>
      )
    case 'mixed':
      return (
        <span className="grounded no">
          ✓ Notes + reference — verify the reference parts
        </span>
      )
    default:
      return (
        <span className="grounded no">
          ⚠ No grounding note — verify this answer
        </span>
      )
  }
}

function sourceBadge(source) {
  return (
    <span className={source === 'drill-notes' ? 'src-notes' : 'src-ref'}>
      {source === 'drill-notes' ? 'Your notes' : 'Reference'}
    </span>
  )
}

/** Animated score count-up on the quiz results screen. */
function ScoreCount({ value, total }) {
  const [n, setN] = useState(0)
  const raf = useRef(null)
  useEffect(() => {
    const start = performance.now()
    const dur = 700
    const tick = (t) => {
      const p = Math.min(1, (t - start) / dur)
      setN(Math.round(value * (1 - Math.pow(1 - p, 3))))
      if (p < 1) raf.current = requestAnimationFrame(tick)
    }
    raf.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf.current)
  }, [value])
  return (
    <div className="quiz-score-num">
      {n} / {total}
    </div>
  )
}

export default function App() {
  const [tab, setTab] = useState('ask')
  const [papers, setPapers] = useState(FALLBACK_PAPERS)
  const [paper, setPaper] = useState('DA')
  const [question, setQuestion] = useState('')
  const [language, setLanguage] = useState('English')
  const [engine, setEngine] = useState('bharatcode')
  const [subject, setSubject] = useState('Probability & Stats')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState(loadHistory)

  // Formula sheet state
  const [kb, setKb] = useState(null)
  const [kbError, setKbError] = useState('')
  const [sheetSubject, setSheetSubject] = useState('Probability & Stats')

  // Quiz state
  const [quizSubject, setQuizSubject] = useState('Probability & Stats')
  const [quiz, setQuiz] = useState(null)
  const [quizIdx, setQuizIdx] = useState(0)
  const [picked, setPicked] = useState(null)
  const [score, setScore] = useState(0)
  const [quizLoading, setQuizLoading] = useState(false)
  const [quizError, setQuizError] = useState('')

  const paperInfo = papers.find((p) => p.code === paper) || FALLBACK_PAPERS[0]
  const subjects = paperInfo.subjects
  const totalNotes = papers.reduce((s, p) => s + (p.total || 0), 0)

  useEffect(() => {
    fetch(`${API_BASE}/api/papers`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d && d.papers && d.papers.length > 0) setPapers(d.papers)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (tab === 'formulas' && !kb && !kbError) {
      fetch(`${API_BASE}/api/kb`)
        .then((r) => {
          if (!r.ok) throw new Error(`Server error (${r.status})`)
          return r.json()
        })
        .then(setKb)
        .catch((e) => setKbError(e.message))
    }
  }, [tab, kb, kbError])

  function changePaper(code) {
    const info = papers.find((p) => p.code === code)
    setPaper(code)
    if (info && info.subjects.length > 0) {
      setSubject(info.subjects[0])
      setSheetSubject(info.subjects[0])
      setQuizSubject(info.subjects[0])
    }
    setResult(null)
    setQuiz(null)
  }

  async function ask(qOverride, paperOverride, subjectOverride) {
    const q = (qOverride ?? question).trim()
    if (!q) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await fetch(`${API_BASE}/api/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: q,
          language,
          subject: subjectOverride ?? subject,
          paper: paperOverride ?? paper,
          engine,
        }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `Server error (${res.status})`)
      }
      const data = await res.json()
      setResult(data)
      setHistory(
        saveHistory({
          question: q,
          language,
          subject: subjectOverride ?? subject,
          paper: paperOverride ?? paper,
          mode: data.mode,
          engine,
          ts: Date.now(),
        }),
      )
    } catch (e) {
      setError(
        e.message === 'Failed to fetch'
          ? 'Could not reach the backend. Is it running? (Locally: uvicorn app:app --port 8000 from backend/.)'
          : e.message,
      )
    } finally {
      setLoading(false)
    }
  }

  function loadExample(ex) {
    if (ex.paper !== paper) changePaper(ex.paper)
    setQuestion(ex.question)
    setLanguage(ex.language)
    setSubject(ex.subject)
    setResult(null)
    setError('')
  }

  function reAsk(entry) {
    if (entry.paper && entry.paper !== paper) changePaper(entry.paper)
    setQuestion(entry.question)
    setLanguage(entry.language)
    setSubject(entry.subject)
    setResult(null)
    setError('')
    setTab('ask')
    ask(entry.question, entry.paper, entry.subject)
  }

  async function startQuiz() {
    setQuizLoading(true)
    setQuizError('')
    setQuiz(null)
    setPicked(null)
    setScore(0)
    setQuizIdx(0)
    try {
      const res = await fetch(
        `${API_BASE}/api/quiz?paper=${encodeURIComponent(paper)}&subject=${encodeURIComponent(quizSubject)}&n=5`,
      )
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `Server error (${res.status})`)
      }
      setQuiz(await res.json())
    } catch (e) {
      setQuizError(e.message)
    } finally {
      setQuizLoading(false)
    }
  }

  function pickOption(idx) {
    if (picked !== null) return
    setPicked(idx)
    if (quiz.questions[quizIdx].correct_index === idx) setScore((s) => s + 1)
  }

  const quizDone = quiz && quizIdx >= quiz.questions.length
  const sheetEntries =
    (kb && kb.papers && kb.papers[paper] && kb.papers[paper][sheetSubject]) || []

  return (
    <div className="page">
      <header className="hero">
        <div className="orb orb-a" />
        <div className="orb orb-b" />
        <div className="orb orb-c" />
        <div className="hero-inner">
          <div className="brand">
            <div className="brand-mark">?</div>
            <h1>
              Doubt<em>Sahayak</em>
            </h1>
          </div>
          <p className="tagline">
            Ask a GATE doubt in Telugu, Hindi or English — get a short
            explanation + one worked example, grounded in GATE notes and
            standard reference material.
          </p>
          <p className="sub">
            All 30 GATE 2027 papers + General Aptitude · Built for CSM
            students · Powered by the BharatCode API ·{' '}
            <a
              href="https://bharatcode.ai/hackathon"
              target="_blank"
              rel="noreferrer"
            >
              BharatCode Build League
            </a>
          </p>
          <div className="stats">
            <div className="stat">
              <b>{totalNotes > 0 ? totalNotes.toLocaleString('en-IN') : '…'}</b>
              <span>notes in the KB</span>
            </div>
            <div className="stat">
              <b>{papers.length}</b>
              <span>GATE papers</span>
            </div>
            <div className="stat">
              <b>3</b>
              <span>languages</span>
            </div>
            <div className="stat">
              <b>{history.length}</b>
              <span>doubts solved</span>
            </div>
          </div>
          <label className="paper-picker">
            GATE paper
            <select value={paper} onChange={(e) => changePaper(e.target.value)}>
              {papers.map((p) => (
                <option key={p.code} value={p.code}>
                  {p.code} — {p.name} ({p.total} notes)
                </option>
              ))}
            </select>
            <span className="paper-meta">
              Now studying: <b>{paperInfo.code} — {paperInfo.name}</b>
            </span>
          </label>
        </div>
      </header>

      <nav className="tabs">
        {[
          ['ask', '✦ Ask a doubt'],
          ['formulas', 'ƒ Formula sheet'],
          ['quiz', '▶ Quiz me'],
          ['history', `↺ History (${history.length})`],
        ].map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={tab === id ? 'active' : ''}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      <div className="tab-panel" key={tab}>
        {tab === 'ask' && (
          <main className="card">
            <div className="row">
              <div>
                <span className="field-label">Answer language</span>
                <div className="seg">
                  {LANGUAGES.map((l) => (
                    <button
                      key={l}
                      type="button"
                      className={language === l ? 'active' : ''}
                      onClick={() => setLanguage(l)}
                    >
                      {LANG_LABELS[l]}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <span className="field-label">Answer engine</span>
                <div className="seg">
                  {ENGINES.map((e) => (
                    <button
                      key={e}
                      type="button"
                      className={engine === e ? 'active' : ''}
                      onClick={() => setEngine(e)}
                    >
                      {ENGINE_LABELS[e]}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            {engine === 'adaption' && (
              <p className="hint">
                Adaption-tuned model, fine-tuned on the GATE knowledge base
                (3,100+ notes, all 30 papers + GA). If the tuned model
                isn&apos;t deployed yet, the answer falls back to BharatCode
                Qwen and says so.
              </p>
            )}

            <div style={{ marginTop: 18 }}>
              <span className="field-label">Subject · {paper}</span>
              <div className="pills">
                {subjects.map((s) => (
                  <button
                    key={s}
                    type="button"
                    className={subject === s ? 'active' : ''}
                    onClick={() => setSubject(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            <label className="q-label">
              Your doubt
              <textarea
                rows={4}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="e.g. What is the difference between P(X ≤ 3) and P(X < 3) for a Binomial variable?"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) ask()
                }}
              />
            </label>

            <div className="examples">
              <span>Try one:</span>
              {EXAMPLES.map((ex) => (
                <button
                  key={ex.label}
                  type="button"
                  onClick={() => loadExample(ex)}
                >
                  {ex.label}
                </button>
              ))}
            </div>

            <button
              className={`ask${loading ? ' loading' : ''}`}
              type="button"
              onClick={() => ask()}
              disabled={loading || !question.trim()}
            >
              {loading && <span className="spinner" />}
              {loading ? 'Thinking…' : '✦ Solve my doubt'}
            </button>
            <p className="hint">Tip: Ctrl/⌘ + Enter also asks.</p>

            {error && <div className="error">{error}</div>}

            {result && (
              <section className="answer">
                <h3>Here&apos;s your answer</h3>
                <div className="badges">
                  <span className={`mode mode-${result.mode}`}>
                    {MODE_LABELS[result.mode] || result.mode}
                  </span>
                  {result.model && <span className="model">{result.model}</span>}
                  {groundingBadge(result)}
                </div>
                {result.warning && <div className="warn">{result.warning}</div>}
                <div className="answer-body">{renderAnswer(result.answer)}</div>
                {result.notes && result.notes.length > 0 && (
                  <details className="notes">
                    <summary>
                      Grounding notes used ({result.notes.length})
                    </summary>
                    <ul>
                      {result.notes.map((n) => (
                        <li key={n.id}>
                          <strong>{n.topic}</strong> {sourceBadge(n.source)}
                          <br />
                          {n.fact}
                          <br />
                          <code>{n.formula}</code>
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </section>
            )}
          </main>
        )}

        {tab === 'formulas' && (
          <main className="card">
            <h2 className="section-title">Formula sheet — {paper}</h2>
            <p className="section-sub">
              Every formula in the knowledge base for {paperInfo.name}, by
              subject. Entries marked {sourceBadge('drill-notes')} come from
              the author&apos;s own GATE DA drill packs;{' '}
              {sourceBadge('reference')} entries are standard textbook material
              — verify them against your notes. Coverage is the full official
              GATE 2027 syllabus topic list; core topics have full notes with
              worked examples, narrower topics have concise notes.
            </p>
            {kbError && <div className="error">{kbError}</div>}
            {kb && (
              <>
                <div className="pills">
                  {subjects.map((s) => (
                    <button
                      key={s}
                      type="button"
                      className={sheetSubject === s ? 'active' : ''}
                      onClick={() => setSheetSubject(s)}
                    >
                      {s} ({kb.summary[paper]?.subjects?.[s] ?? 0})
                    </button>
                  ))}
                </div>
                <ul className="sheet">
                  {sheetEntries.map((e, i) => (
                    <li
                      key={e.id}
                      style={{ animationDelay: `${Math.min(i, 10) * 45}ms` }}
                    >
                      <div className="sheet-head">
                        <strong>{e.topic}</strong>{' '}
                        <span className="badges-row">
                          {sourceBadge(e.source)}{' '}
                          {e.depth && (
                            <span
                              className={
                                e.depth === 'full' ? 'depth-full' : 'depth-concise'
                              }
                            >
                              {e.depth === 'full' ? 'In depth' : 'Concise'}
                            </span>
                          )}
                        </span>
                      </div>
                      <code className="sheet-formula">{e.formula}</code>
                      <p>{e.fact}</p>
                      <p className="sheet-example">
                        <em>Example:</em> {e.example}
                      </p>
                    </li>
                  ))}
                </ul>
                {sheetEntries.length === 0 && (
                  <p className="empty">
                    No notes for this subject yet.
                  </p>
                )}
              </>
            )}
          </main>
        )}

        {tab === 'quiz' && (
          <main className="card">
            <h2 className="section-title">Quiz me — {paper}</h2>
            <p className="section-sub">
              Five multiple-choice questions built from the knowledge base for{' '}
              {paperInfo.name} — match a formula to its topic, or a topic to
              its formula. Instant feedback, score at the end.
            </p>
            {!quiz && (
              <div className="row">
                <label>
                  Subject ({paper})
                  <select
                    value={quizSubject}
                    onChange={(e) => setQuizSubject(e.target.value)}
                  >
                    {subjects.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  className={`ask quiz-start${quizLoading ? ' loading' : ''}`}
                  type="button"
                  onClick={startQuiz}
                  disabled={quizLoading}
                >
                  {quizLoading && <span className="spinner" />}
                  {quizLoading ? 'Building quiz…' : '▶ Start quiz'}
                </button>
              </div>
            )}
            {quizError && <div className="error">{quizError}</div>}
            {quiz && !quizDone && (
              <section className="quiz-q">
                <div className="quiz-progress-wrap">
                  <div
                    className="quiz-progress-bar"
                    style={{
                      width: `${(quizIdx / quiz.questions.length) * 100}%`,
                    }}
                  />
                </div>
                <p className="quiz-progress">
                  Question {quizIdx + 1} of {quiz.questions.length} · Score:{' '}
                  {score} · {quiz.questions[quizIdx].subject}
                </p>
                {quiz.pool_note && (
                  <p className="quiz-note">{quiz.pool_note}</p>
                )}
                <p className="quiz-prompt">
                  {quiz.questions[quizIdx].prompt.split('\n').map((l, i) => (
                    <span key={i}>
                      {l}
                      <br />
                    </span>
                  ))}
                </p>
                <div className="quiz-options">
                  {quiz.questions[quizIdx].options.map((opt, i) => {
                    const correct = quiz.questions[quizIdx].correct_index === i
                    const isPicked = picked === i
                    let cls = ''
                    if (picked !== null) {
                      if (correct) cls = 'correct'
                      else if (isPicked) cls = 'wrong'
                    }
                    return (
                      <button
                        key={`${quizIdx}-${i}`}
                        type="button"
                        className={cls}
                        onClick={() => pickOption(i)}
                        disabled={picked !== null}
                      >
                        {opt}
                      </button>
                    )
                  })}
                </div>
                {picked !== null && (
                  <div className="quiz-feedback">
                    {picked === quiz.questions[quizIdx].correct_index ? (
                      <p className="good">✓ Correct — nice one!</p>
                    ) : (
                      <p className="bad">
                        ✗ Not quite — the right answer is:{' '}
                        <strong>
                          {quiz.questions[quizIdx].answer}
                        </strong>
                      </p>
                    )}
                    <button
                      type="button"
                      className="ask"
                      onClick={() => {
                        setQuizIdx((i) => i + 1)
                        setPicked(null)
                      }}
                    >
                      {quizIdx + 1 === quiz.questions.length
                        ? 'See my score'
                        : 'Next question →'}
                    </button>
                  </div>
                )}
              </section>
            )}
            {quiz && quizDone && (
              <section className="quiz-done">
                <ScoreCount value={score} total={quiz.questions.length} />
                <h3>
                  {score === quiz.questions.length
                    ? 'Perfect score! 🎉'
                    : score >= 3
                      ? 'Solid work!'
                      : 'Good start — keep drilling!'}
                </h3>
                <p>
                  {score === quiz.questions.length
                    ? 'Perfect — this subject is yours. 🎉'
                    : score >= 3
                      ? 'Solid. Re-read the ones you missed in the formula sheet.'
                      : 'Keep drilling — the formula sheet for this subject is one tab away.'}
                </p>
                <button
                  type="button"
                  className="ask"
                  onClick={() => {
                    setQuiz(null)
                    setPicked(null)
                    setScore(0)
                    setQuizIdx(0)
                  }}
                >
                  ↺ Play again
                </button>
              </section>
            )}
          </main>
        )}

        {tab === 'history' && (
          <main className="card">
            <h2 className="section-title">Recent doubts</h2>
            <p className="section-sub">
              Your last {history.length} doubt{history.length === 1 ? '' : 's'},
              saved in this browser. Click one to ask it again.
            </p>
            {history.length === 0 && (
              <p className="empty">
                <span className="empty-illo">💭</span>
                No doubts yet — ask one from the Ask tab and it will show up
                here.
              </p>
            )}
            <ul className="history">
              {history.map((h, i) => (
                <li key={`${h.ts}-${i}`} style={{ animationDelay: `${Math.min(i, 8) * 40}ms` }}>
                  <button type="button" onClick={() => reAsk(h)}>
                    <span className="h-q">{h.question}</span>
                    <span className="h-meta">
                      {h.paper || 'DA'} · {h.subject} · {h.language} ·{' '}
                      {new Date(h.ts).toLocaleString()}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            {history.length > 0 && (
              <button
                type="button"
                className="clear-history"
                onClick={() => {
                  localStorage.removeItem(HISTORY_KEY)
                  setHistory([])
                }}
              >
                Clear history
              </button>
            )}
          </main>
        )}
      </div>

      <footer>
        <p>
          Knowledge base covers the full official GATE 2027 syllabus topic
          list for all 30 papers plus General Aptitude. Core topics have
          full notes with worked examples; narrower topics have concise
          notes. Entries from the author&apos;s own drill packs are labelled
          &ldquo;Your notes&rdquo; (DA only); everything else is standard
          reference material and should be verified against your notes.
          Offline mode answers from the knowledge base only and says so.
        </p>
      </footer>
    </div>
  )
}
