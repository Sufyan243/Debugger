import { motion } from "framer-motion"

const images = [
  { src: "/images/Gemini_Generated_Image_e8to7be8to7be8to.webp", alt: "Developer debugging Python at night" },
  { src: "/images/Gemini_Generated_Image_faxv5dfaxv5dfaxv.webp", alt: "Student learning to code with focus" },
  { src: "/images/Gemini_Generated_Image_qk03riqk03riqk03.webp", alt: "Programmer reading error output on screen" },
]

export default function Gallery() {
  return (
    <section className="py-16 px-6">
      <div className="max-w-5xl mx-auto grid grid-cols-1 sm:grid-cols-3 gap-4">
        {images.map((img, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: i * 0.08 }}
            className="rounded-xl overflow-hidden border border-white/10 shadow-lg"
          >
            <img
              src={img.src}
              alt={img.alt}
              className="w-full object-cover h-52"
            />
          </motion.div>
        ))}
      </div>
    </section>
  )
}
