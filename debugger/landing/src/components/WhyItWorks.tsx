import { motion } from "framer-motion"

const TOOL_URL = "http://localhost:5173"

const bullets = [
  { title: "Built for beginners", desc: "No jargon, no assumptions, just clear explanations" },
  { title: "Safe sandbox execution", desc: "Docker-isolated Python 3.11, nothing runs on your machine" },
  { title: "Concept-based learning", desc: "Understand the why, not just the fix" },
  { title: "No installation required", desc: "Runs entirely in your browser, open and start" },
]

export default function WhyItWorks() {
  return (
    <section className="py-24 px-6 bg-card/20">
      <div className="max-w-5xl mx-auto flex flex-col items-center gap-20">

        <div className="w-full flex flex-col lg:flex-row items-center gap-14">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4 }}
            className="flex-1"
          >
            <h2 className="text-3xl sm:text-4xl font-bold text-bright mb-10">Why it works</h2>
            <div className="flex flex-col gap-4">
              {bullets.map((b, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -12 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.35, delay: i * 0.07 }}
                  className="bg-card rounded-lg px-5 py-4 border border-white/5 flex flex-col gap-1"
                >
                  <span className="text-bright font-semibold text-sm">{b.title}</span>
                  <span className="text-muted text-sm">{b.desc}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 16 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="flex-1 rounded-xl overflow-hidden border border-white/10 shadow-xl"
          >
            <img
              src="/images/Gemini_Generated_Image_c1z4n0c1z4n0c1z4.webp"
              alt="Developer focused at laptop with code on screen"
              className="w-full object-cover h-72 lg:h-80"
            />
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
          className="text-center flex flex-col items-center gap-4"
        >
          <h2 className="text-3xl sm:text-4xl font-bold text-bright">Ready to debug smarter?</h2>
          <p className="text-muted text-lg">Your first debug session takes under 30 seconds.</p>
          <p className="text-muted/50 text-sm">No setup. No credit card. Start in one click.</p>
          <a
            href={TOOL_URL}
            target="_blank"
            rel="noreferrer"
            className="mt-2 inline-flex items-center gap-2 bg-accent hover:bg-accent/90 text-white font-semibold px-10 py-4 rounded-lg transition-all hover:shadow-[0_0_28px_rgba(99,102,241,0.45)] text-base"
          >
            Open Debugger
          </a>
        </motion.div>

      </div>
    </section>
  )
}
