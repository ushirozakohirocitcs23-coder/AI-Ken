import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { BookOpen, CheckCircle2, Heart, Languages, Lock, ScrollText, Sparkles } from 'lucide-react'
import { Badge, Button, Logo } from '../components/ui'
import { useAuth } from '../auth'

const DEMO = [
  {
    lang: 'English', form: 'Quatrain · AABB',
    story: 'I always try my best to make everyone happy, but sometimes I feel like nobody notices my efforts. I smile in front of everyone, even when I feel tired inside.',
    title: 'Behind My Smile',
    poem: 'I wear a smile beneath the light,\nWhile hiding tears beyond their sight.\nI give my best, yet feel unseen,\nA tired heart behind a cheerful scene.',
    emotions: ['Sadness', 'Loneliness', 'Hope', 'Exhaustion'],
  },
  {
    lang: 'Filipino', form: 'Tanaga · 7-7-7-7',
    story: 'Masaya ako kapag kasama ko ang pamilya ko, pero minsan nalulungkot ako kapag iniisip ko ang mga pangarap na hindi ko pa naaabot.',
    title: 'Sa Piling Mo',
    poem: 'Sa piling ng pamilya\nPuso ko\'y may ligaya\nPangarap ay may luha\nNgunit may pag-asa pa',
    emotions: ['Saya', 'Lungkot', 'Pag-asa'],
  },
]

export default function Landing() {
  const { user } = useAuth()
  const [i, setI] = useState(0)
  const [typed, setTyped] = useState('')
  const d = DEMO[i]
  useEffect(() => {
    setTyped('')
    let n = 0
    const t = setInterval(() => { n += 2; setTyped(d.poem.slice(0, n)); if (n >= d.poem.length) clearInterval(t) }, 28)
    return () => clearInterval(t)
  }, [i, d.poem])
  const home = user ? (user.role === 'admin' ? '/admin' : '/app') : null

  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5">
        <Logo />
        <nav className="flex items-center gap-2">
          {home ? <Link to={home}><Button>Open AI-KEN</Button></Link> : <>
            <Link to="/login"><Button variant="ghost">Log in</Button></Link>
            <Link to="/register"><Button>Sign up</Button></Link>
          </>}
        </nav>
      </header>

      <section className="glow">
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-5 pb-20 pt-10 lg:grid-cols-[1.05fr_1fr] lg:pt-16">
          <div className="rise">
            <Badge tone="iris" className="mb-5"><Sparkles className="h-3 w-3" /> Filipino · English · Taglish</Badge>
            <h1 className="font-serif text-4xl font-semibold leading-[1.1] tracking-tight sm:text-5xl lg:text-6xl">
              Your Story, Your Emotions, <span className="bg-gradient-to-r from-iris-300 to-sky2-400 bg-clip-text text-transparent">Your Poetry.</span>
            </h1>
            <p className="mt-5 max-w-xl text-lg text-ink-300">Turn the moments you live and the feelings you carry into meaningful poetry.</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to={home || '/register'}><Button size="lg">{home ? 'Continue writing' : 'Start writing — it\'s free'}</Button></Link>
              {!home && <Link to="/login"><Button size="lg" variant="secondary">I have an account</Button></Link>}
            </div>
            <p className="mt-4 text-xs text-ink-400">Emotion detection is an interpretation of your words — not a diagnosis.</p>
          </div>

          <div className="rise rounded-3xl border border-ink-700 bg-ink-850/80 p-5 shadow-2xl shadow-iris-900/20 sm:p-6" aria-label="Story-to-poem demonstration">
            <div className="mb-4 flex gap-2" role="tablist">
              {DEMO.map((x, k) => (
                <button key={x.lang} role="tab" aria-selected={i === k} onClick={() => setI(k)}
                  className={`focus-ring rounded-full px-3 py-1 text-xs font-medium ${i === k ? 'bg-iris-500 text-white' : 'bg-ink-800 text-ink-300 hover:text-ink-100'}`}>{x.lang}</button>
              ))}
            </div>
            <div className="ml-auto w-fit max-w-[90%] rounded-2xl rounded-tr-sm bg-ink-700 px-4 py-3 text-sm text-ink-100">{d.story}</div>
            <div className="mt-4 rounded-2xl border border-ink-700 bg-ink-900/70 p-5">
              <div className="mb-2 flex items-center justify-between"><p className="font-serif text-lg font-semibold">{d.title}</p><Badge tone="iris">{d.form}</Badge></div>
              <p className="poem-text min-h-[8.5rem] text-[15px] text-ink-100">{typed}<span className="dot text-iris-400">▍</span></p>
              <div className="mt-3 flex flex-wrap gap-1.5">{d.emotions.map(e => <Badge key={e}>{e}</Badge>)}</div>
              <p className="mt-3 flex items-center gap-1.5 text-xs text-emerald-300"><CheckCircle2 className="h-3.5 w-3.5" /> Structure validated</p>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-16">
        <h2 className="font-serif text-3xl font-semibold tracking-tight">Poetry that listens first</h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[
            [Heart, 'Emotion-aware', 'AI-KEN reads your story for joy, grief, hope, frustration, loneliness and mixed feelings — then writes with empathy, never judgment.'],
            [Languages, 'Filipino, English & Taglish', 'Write the way you speak. Get natural Filipino, expressive English, or Taglish — and translate between them.'],
            [ScrollText, 'Real poetic forms', 'Haiku, tanka, sonnets, limericks, ballads, diamante — and Filipino forms like tanaga, diona, dalit, awit and korido.'],
            [CheckCircle2, 'Transparent validation', 'Every poem gets a report: line counts, syllables per line, rhyme scheme and acrostic letters — checked, not just claimed.'],
            [BookOpen, 'Learn new words', 'Tap into a Filipino–English vocabulary with meanings, synonyms, antonyms and examples — with clear sources.'],
            [Sparkles, 'Grounded with RAG', 'Before writing, AI-KEN retrieves poetry rules, literary techniques and dictionary entries from its knowledge base.'],
          ].map(([Icon, t, d]) => (
            <div key={t} className="rounded-2xl border border-ink-700 bg-ink-850/60 p-5">
              <Icon className="h-5 w-5 text-iris-400" aria-hidden="true" />
              <h3 className="mt-3 font-semibold">{t}</h3>
              <p className="mt-1.5 text-sm text-ink-300">{d}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 pb-20">
        <div className="flex flex-col items-start gap-4 rounded-3xl border border-ink-700 bg-gradient-to-br from-iris-600/20 to-sky-600/10 p-8 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="flex items-center gap-2 text-sm text-ink-300"><Lock className="h-4 w-4" /> Your stories stay private</p>
            <p className="mt-1 font-serif text-2xl font-semibold">Every feeling has a story. Every story deserves to be heard.</p>
          </div>
          <Link to={home || '/register'}><Button size="lg">Write your first poem</Button></Link>
        </div>
      </section>

      <footer className="border-t border-ink-800">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-5 py-6 text-sm text-ink-400">
          <Logo size="sm" />
          <div className="flex gap-4"><Link to="/privacy" className="hover:text-ink-100">Privacy</Link><span>© {new Date().getFullYear()} AI-KEN</span></div>
        </div>
      </footer>
    </div>
  )
}
