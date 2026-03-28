export default function Footer() {
  return (
    <footer className="border-t border-white/5 py-8 px-6">
      <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <span className="text-muted text-sm">© 2026 Terra Debugger</span>
        <div className="flex items-center gap-6 text-sm text-muted">
          <a href="#how-it-works" className="hover:text-bright transition-colors">How it works</a>
          <a href="/privacy" className="hover:text-bright transition-colors">Privacy</a>
          <a href="mailto:terra.debugger.ai@gmail.com" className="hover:text-bright transition-colors">Contact</a>
        </div>
      </div>
    </footer>
  )
}
