import { useState } from "react"
import { motion } from "framer-motion"
import LandingAuthModal from "./LandingAuthModal"

const TOOL_URL = import.meta.env.VITE_TOOL_URL ?? "http://localhost:5173"

export default function Hero() {
  const [showAuth, setShowAuth] = useState(false)

  return (
    <section className="min-h-screen flex flex-col">
      <nav className="flex items-center justify-between px-8 py-5 border-b border-white/5">
        <span className="text-bright font-bold text-lg tracking-tight">Terra Debugger</span>
        <div className="flex items-center gap-8">
          <a href="#how-it-works" className="text-muted hover:text-bright text-sm transition-colors">How it works</a>
          <button
            onClick={() => setShowAuth(true)}
            className="text-sm font-semibold text-accent border border-accent/30 hover:border-accent/60 px-4 py-1.5 rounded-lg transition-all bg-transparent cursor-pointer"
          >
            Sign in
          </button>
        </div>
      </nav>

      <div className="flex flex-col items-center justify-center flex-1 text-center px-6 pt-20 pb-16 gap-10">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="flex flex-col items-center gap-5"
        >
          <div className="text-xs font-semibold tracking-widest text-accent uppercase bg-accent/10 px-4 py-1.5 rounded-full">
            Free · No signup · Runs in browser
          </div>
          <h1 className="text-4xl sm:text-6xl font-bold text-bright leading-tight max-w-3xl">
            Stop Googling Your Errors.<br />Start Understanding Them.
          </h1>
          <p className="text-muted text-lg sm:text-xl max-w-xl leading-relaxed">
            Run Python safely. Get plain-English explanations. Fix problems like a real developer.
          </p>
          <div className="flex items-center gap-4 mt-2">
            <a
              href={TOOL_URL}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 bg-accent hover:bg-accent/90 text-white font-semibold px-8 py-3.5 rounded-lg transition-all hover:shadow-[0_0_24px_rgba(99,102,241,0.4)] text-base"
            >
              Start Debugging Free
            </a>
            <span className="text-muted/50 text-sm">One click to start</span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15 }}
          className="w-full max-w-5xl flex flex-col items-center gap-3"
        >
          <p className="text-muted/50 text-xs uppercase tracking-widest font-semibold">This is the tool</p>
          <div className="w-full rounded-xl overflow-hidden shadow-[0_0_60px_rgba(99,102,241,0.15)] ring-1 ring-accent/20">
            <div className="bg-card px-4 py-2.5 flex items-center gap-2 border-b border-white/5">
              <span className="w-2.5 h-2.5 rounded-full bg-danger/60" />
              <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/60" />
              <span className="w-2.5 h-2.5 rounded-full bg-success/60" />
              <span className="ml-3 text-muted/50 text-xs font-mono">terra-debugger.app</span>
            </div>
            <img
              src="/images/exac.webp"
              alt="Terra Debugger app showing Python editor and error feedback"
              className="w-full object-cover"
            />
          </div>
        </motion.div>
      </div>
      {showAuth && <LandingAuthModal onClose={() => setShowAuth(false)} />}
    </section>
  )
}
