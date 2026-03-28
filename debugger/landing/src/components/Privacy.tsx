export default function Privacy() {
  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0f", color: "#f9fafb", padding: "60px 24px" }}>
      <div style={{ maxWidth: 720, margin: "0 auto" }}>
        <a href="/" style={{ color: "#6366f1", fontSize: 14, textDecoration: "none", display: "inline-block", marginBottom: 32 }}>← Back to Terra Debugger</a>
        <h1 style={{ fontSize: 32, fontWeight: 700, marginBottom: 8 }}>Privacy Policy</h1>
        <p style={{ color: "#6b7280", fontSize: 14, marginBottom: 40 }}>Last updated: March 2026</p>

        {[
          {
            title: "What we collect",
            body: "We collect your email address and OAuth profile (name, avatar) when you sign in with Google or GitHub. We store the Python code you submit and its execution results to power your progress dashboard."
          },
          {
            title: "How we use it",
            body: "Your data is used solely to provide the Terra Debugger service — running your code, showing your session history, and tracking your learning progress. We do not sell your data or use it for advertising."
          },
          {
            title: "Code execution",
            body: "Code you submit is executed in an isolated Docker sandbox. It is stored in our database linked to your session so you can review your history. We do not share your code with third parties."
          },
          {
            title: "Authentication",
            body: "We use GitHub and Google OAuth for sign-in. We receive only the profile information those providers share (email, name, avatar). Passwords for email accounts are hashed using bcrypt and never stored in plain text."
          },
          {
            title: "Cookies",
            body: "We use a single httpOnly session cookie to keep you signed in. No tracking or advertising cookies are used."
          },
          {
            title: "Data retention",
            body: "Your account and session data is retained as long as your account exists. You can request deletion by emailing us."
          },
          {
            title: "Contact",
            body: "For any privacy questions or data deletion requests, email us at terra.debugger.ai@gmail.com."
          },
        ].map(({ title, body }) => (
          <div key={title} style={{ marginBottom: 32 }}>
            <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, color: "#f9fafb" }}>{title}</h2>
            <p style={{ color: "#9ca3af", fontSize: 15, lineHeight: 1.7 }}>{body}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
