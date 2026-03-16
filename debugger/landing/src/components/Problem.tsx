import { motion } from "framer-motion"

const rows = [
  { habit: "Copy errors blindly", outcome: "Random fixes", result: "No learning" },
  { habit: "Guess solutions", outcome: "More confusion", result: "Frustration" },
  { habit: "Memorize syntax", outcome: "Breaks again", result: "No mastery" },
]

export default function Problem() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
          className="text-center mb-14"
        >
          <h2 className="text-3xl sm:text-4xl font-bold text-bright mb-4">Sound familiar?</h2>
          <p className="text-muted text-lg">Most beginners debug the same broken way.</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="rounded-xl border border-white/10 overflow-hidden"
        >
          <div className="grid grid-cols-3 bg-card/80 px-6 py-3 border-b border-white/5">
            <span className="text-xs font-semibold text-muted uppercase tracking-wider">What beginners do</span>
            <span className="text-xs font-semibold text-muted uppercase tracking-wider">What happens</span>
            <span className="text-xs font-semibold text-muted uppercase tracking-wider">Result</span>
          </div>
          {rows.map((row, i) => (
            <div key={i} className="grid grid-cols-3 px-6 py-4 border-b border-white/5 last:border-0 bg-card/40 hover:bg-card/60 transition-colors">
              <span className="text-danger/80 text-sm">{row.habit}</span>
              <span className="text-muted text-sm">{row.outcome}</span>
              <span className="text-muted/60 text-sm">{row.result}</span>
            </div>
          ))}
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="text-center mt-10 text-bright text-xl font-semibold"
        >
          👉 Debugging is a <span className="text-accent">thinking skill</span> — not a search skill.
        </motion.p>
      </div>
    </section>
  )
}
