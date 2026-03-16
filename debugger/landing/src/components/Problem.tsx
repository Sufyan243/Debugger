import { motion } from "framer-motion"

const rows = [
  { habit: "Copy errors blindly", outcome: "Random fixes", result: "No learning" },
  { habit: "Guess solutions", outcome: "More confusion", result: "Frustration" },
  { habit: "Memorize syntax", outcome: "Breaks again", result: "No mastery" },
]

export default function Problem() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-5xl mx-auto flex flex-col lg:flex-row items-center gap-14">

        <motion.div
          initial={{ opacity: 0, x: -16 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
          className="flex-1 min-w-0"
        >
          <h2 className="text-3xl sm:text-4xl font-bold text-bright mb-4">Sound familiar?</h2>
          <p className="text-muted text-lg mb-10">Most beginners debug the same broken way.</p>

          <div className="rounded-xl border border-white/10 overflow-hidden">
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
          </div>

          <p className="mt-8 text-bright text-lg font-semibold">
            Debugging is a <span className="text-accent">thinking skill</span>, not a search skill.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 16 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="flex-1 min-w-0 rounded-xl overflow-hidden border border-white/10 shadow-xl"
        >
          <img
            src="/images/Gemini_Generated_Image_4pzyuj4pzyuj4pzy.webp"
            alt="Student frustrated while debugging code"
            className="w-full object-cover h-72 lg:h-full"
          />
        </motion.div>

      </div>
    </section>
  )
}
