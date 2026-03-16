import { motion } from "framer-motion"

const TOOL_URL = "/app"

const editorPreview = `def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)

scores = [85, 92, 78, 95, 88]
print(calculate_average(scores))`

export default function Hero() {
  return (
    <section className="min-h-screen flex flex-col">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-white/5">
        <span className="text-bright font-bold text-lg tracking-tight">⬡ Cognitive Debugger</span>
        <div className="flex items-center gap-8">
          <a href="#how-it-works" className="text-muted hover:text-bright text-sm transition-colors">Docs</a>
          <a href="https://github.com/Sufyan243/Debugger" target="_blank" rel="noreferrer" className="text-muted hover:text-bright text-sm transition-colors">GitHub</a>
        </div>
      </nav>

      {/* Hero content */}
      <div className="flex flex-col items-center justify-center flex-1 text-center px-6 pt-20 pb-16 gap-8">
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
            Learn Python Debugging<br />by Thinking — Not Guessing.
          </h1>
          <p className="text-muted text-lg sm:text-xl max-w-xl leading-relaxed">
            Run code safely. Understand errors. Fix problems like a real developer.
          </p>
          <a
            href={TOOL_URL}
            className="mt-2 inline-flex items-center gap-2 bg-accent hover:bg-accent/90 text-white font-semibold px-8 py-3.5 rounded-lg transition-all hover:shadow-[0_0_24px_rgba(99,102,241,0.4)] text-base"
          >
            Start Debugging →
          </a>
        </motion.div>

        {/* Editor preview */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15 }}
          className="w-full max-w-3xl rounded-xl border border-white/10 overflow-hidden shadow-2xl"
        >
          <div className="bg-card px-4 py-3 flex items-center gap-2 border-b border-white/5">
            <span className="w-3 h-3 rounded-full bg-danger/70" />
            <span className="w-3 h-3 rounded-full bg-yellow-500/70" />
            <span className="w-3 h-3 rounded-full bg-success/70" />
            <span className="ml-3 text-muted text-xs font-mono">main.py</span>
          </div>
          <div className="bg-[#0d1117] p-6 text-left">
            <pre className="text-sm font-mono leading-relaxed overflow-x-auto">
              {editorPreview.split("\n").map((line, i) => (
                <div key={i} className="flex gap-4">
                  <span className="text-muted/40 select-none w-4 text-right shrink-0">{i + 1}</span>
                  <span className={
                    line.startsWith("def ") ? "text-[#79c0ff]" :
                    line.includes("return") ? "text-[#ff7b72]" :
                    line.includes("print") ? "text-[#d2a8ff]" :
                    line.startsWith("#") ? "text-muted" :
                    "text-[#e6edf3]"
                  }>{line || " "}</span>
                </div>
              ))}
            </pre>
            <div className="mt-4 pt-4 border-t border-white/5 flex items-start gap-3">
              <span className="text-success text-xs font-mono mt-0.5">✓</span>
              <div>
                <p className="text-success text-xs font-semibold">Output: 87.6</p>
                <p className="text-muted text-xs mt-1">Great — your loop accumulates correctly. Now try predicting the output before running.</p>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
