export default function Footer() {
  return (
    <footer className="border-t border-white/5 py-8 px-6">
      <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <span className="text-muted text-sm">Cognitive Debugger</span>
        <div className="flex items-center gap-6 text-sm text-muted">
          <a href="https://github.com/Sufyan243/Debugger" target="_blank" rel="noreferrer" className="hover:text-bright transition-colors">GitHub</a>
          <a href="#how-it-works" className="hover:text-bright transition-colors">Docs</a>
          <span className="text-muted/40">Privacy</span>
        </div>
      </div>
    </footer>
  )
}
