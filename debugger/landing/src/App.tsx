import Hero from "./components/Hero"
import Problem from "./components/Problem"
import Solution from "./components/Solution"
import HowItWorks from "./components/HowItWorks"
import WhyItWorks from "./components/WhyItWorks"
import Footer from "./components/Footer"
import Privacy from "./components/Privacy"

export default function App() {
  const isPrivacy = window.location.pathname === "/privacy"
  if (isPrivacy) return <Privacy />

  return (
    <main className="bg-bg text-bright font-sans">
      <Hero />
      <Problem />
      <Solution />
      <HowItWorks />
      <WhyItWorks />
      <Footer />
    </main>
  )
}
