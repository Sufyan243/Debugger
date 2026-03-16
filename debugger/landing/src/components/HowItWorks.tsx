import { motion } from "framer-motion"

const steps = [
  { label: "Paste your Python code", detail: "Any snippet, beginner or intermediate" },
  { label: "Predict what will happen", detail: "Optional but powerful, builds intuition" },
  { label: "Run in secure sandbox", detail: "Isolated Docker container, zero risk" },
  { label: "See explanation of errors", detail: "Not stack traces, actual understanding" },
  { label: "Get guided fixes", detail: "Hints that make you think, not copy-paste" },
]

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="py-24 px-6">
      <div className="max-w-5xl mx-auto flex flex-col lg:flex-row items-center gap-14">

        <motion.div
          initial={{ opacity: 0, x: -16 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
          className="flex-1 rounded-xl overflow-hidden border border-white/10 shadow-xl"
        >
          <img
            src="/images/Gemini_Generated_Image_abkbuaabkbuaabkb.webp"
            alt="Close up of code on a screen in a dark environment"
            className="w-full object-cover h-80 lg:h-full"
          />
        </motion.div>

        <div className="flex-1">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4 }}
            className="mb-10"
          >
            <h2 className="text-3xl sm:text-4xl font-bold text-bright mb-4">How it works</h2>
            <p className="text-muted text-lg">Five steps. Under 30 seconds to your first insight.</p>
          </motion.div>

          <div className="flex flex-col gap-0">
            {steps.map((step, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: 16 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.35, delay: i * 0.08 }}
                className="flex gap-5"
              >
                <div className="flex flex-col items-center">
                  <div className="w-8 h-8 rounded-full bg-accent/20 border border-accent/40 flex items-center justify-center text-accent text-xs font-bold shrink-0">
                    {i + 1}
                  </div>
                  {i < steps.length - 1 && <div className="w-px flex-1 bg-white/5 my-1" />}
                </div>
                <div className="pb-8">
                  <p className="text-bright font-semibold text-sm">{step.label}</p>
                  <p className="text-muted text-sm mt-1">{step.detail}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

      </div>
    </section>
  )
}
