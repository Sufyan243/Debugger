import { motion } from "framer-motion"

const cards = [
  { icon: "✍️", title: "Write Code", desc: "Paste or type any Python snippet" },
  { icon: "🛡️", title: "Run Safely", desc: "Isolated sandbox — nothing breaks your machine" },
  { icon: "🔍", title: "Understand Error", desc: "Plain-English explanation of what went wrong" },
  { icon: "🧠", title: "Fix with Guidance", desc: "Cognitive hints that teach, not just solve" },
]

export default function Solution() {
  return (
    <section className="py-24 px-6 bg-card/20">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
          className="text-center mb-14"
        >
          <h2 className="text-3xl sm:text-4xl font-bold text-bright mb-4">The smarter way to debug</h2>
          <p className="text-muted text-lg">Every step is designed to build your mental model.</p>
        </motion.div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {cards.map((card, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.08 }}
              className="bg-card rounded-xl p-6 border border-white/5 flex flex-col gap-3"
            >
              <span className="text-2xl">{card.icon}</span>
              <div className="flex items-center gap-2">
                <span className="text-accent text-xs font-bold">{i + 1}</span>
                <span className="text-bright font-semibold text-sm">{card.title}</span>
              </div>
              <p className="text-muted text-sm leading-relaxed">{card.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
