import { motion } from "framer-motion"

const TOOL_URL = "/app"

const bullets = [
  "Built for beginners — no jargon, no assumptions",
  "Safe sandbox execution — Docker-isolated Python 3.11",
  "Concept-based learning — understand the why, not just the fix",
  "No installation required — runs entirely in your browser",
]

export default function WhyItWorks() {
  return (
    <section className="py-24 px-6 bg-card/20">
      <div className="max-w-3xl mx-auto flex flex-col items-center gap-16">

        {/* Why it works */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
          className="w-full"
        >
          <h2 className="text-3xl sm:text-4xl font-bold text-bright mb-10 text-center">Why it works</h2>
          <div className="flex flex-col gap-4">
            {bullets.map((b, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -12 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.35, delay: i * 0.07 }}
                className="flex items-start gap-3 bg-card rounded-lg px-5 py-4 border border-white/5"
              >
                <span className="text-success mt-0.5 shrink-0">✅</span>
                <span className="text-bright/80 text-sm">{b}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Final CTA */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
          className="text-center flex flex-col items-center gap-6"
        >
          <h2 className="text-3xl sm:text-4xl font-bold text-bright">Ready to debug smarter?</h2>
          <p className="text-muted text-lg">No signup. No setup. Just open and start.</p>
          <a
            href={TOOL_URL}
            className="inline-flex items-center gap-2 bg-accent hover:bg-accent/90 text-white font-semibold px-10 py-4 rounded-lg transition-all hover:shadow-[0_0_28px_rgba(99,102,241,0.45)] text-base"
          >
            Open Debugger
          </a>
        </motion.div>

      </div>
    </section>
  )
}
