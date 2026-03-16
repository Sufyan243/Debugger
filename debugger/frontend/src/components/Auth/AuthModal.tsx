import { useState } from "react";

const BASE = `${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}/api/v1`;
const BACKEND = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

interface Props {
  onAuth: (token: string, emailOrUser: string, avatar: string) => void;
  onClose: () => void;
}

export default function AuthModal({ onAuth, onClose }: Props) {
  const [mode, setMode] = useState<"options" | "email">("options");
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submitEmail(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const endpoint = isLogin ? "login" : "register";
      const res = await fetch(`${BASE}/auth/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Something went wrong");
      onAuth(data.access_token, data.email ?? email, data.avatar_url ?? "");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  const overlay: React.CSSProperties = {
    position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)",
    display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50,
  };
  const card: React.CSSProperties = {
    background: "#111827", border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 16, padding: "36px 32px", width: 380, position: "relative",
  };
  const providerBtn: React.CSSProperties = {
    width: "100%", display: "flex", alignItems: "center", gap: 12,
    background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 8, padding: "11px 16px", color: "#f9fafb", fontSize: 14,
    fontWeight: 500, cursor: "pointer", transition: "background 0.15s",
  };

  return (
    <div style={overlay} onClick={onClose}>
      <div style={card} onClick={e => e.stopPropagation()}>
        <button onClick={onClose} style={{ position: "absolute", top: 14, right: 16, background: "none", border: "none", color: "#6b7280", fontSize: 18, cursor: "pointer" }}>✕</button>

        {mode === "options" && (
          <>
            <h2 style={{ color: "#f9fafb", fontWeight: 700, fontSize: 20, marginBottom: 6 }}>Welcome back</h2>
            <p style={{ color: "#6b7280", fontSize: 14, marginBottom: 28 }}>Sign in to save your progress and share your wins.</p>

            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <button
                style={providerBtn}
                onClick={() => window.location.href = `${BACKEND}/api/v1/auth/github`}
                onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.08)")}
                onMouseLeave={e => (e.currentTarget.style.background = "rgba(255,255,255,0.04)")}
              >
                <GitHubIcon />
                Continue with GitHub
              </button>

              <button
                style={providerBtn}
                onClick={() => window.location.href = `${BACKEND}/api/v1/auth/google`}
                onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.08)")}
                onMouseLeave={e => (e.currentTarget.style.background = "rgba(255,255,255,0.04)")}
              >
                <GoogleIcon />
                Continue with Google
              </button>

              <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "4px 0" }}>
                <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.06)" }} />
                <span style={{ color: "#4b5563", fontSize: 12 }}>or</span>
                <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.06)" }} />
              </div>

              <button
                style={{ ...providerBtn, justifyContent: "center" }}
                onClick={() => setMode("email")}
                onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.08)")}
                onMouseLeave={e => (e.currentTarget.style.background = "rgba(255,255,255,0.04)")}
              >
                Continue with Email
              </button>
            </div>

            <p style={{ color: "#4b5563", fontSize: 12, textAlign: "center", marginTop: 20 }}>
              By continuing you agree to our Terms and Privacy Policy.
            </p>
          </>
        )}

        {mode === "email" && (
          <>
            <button onClick={() => setMode("options")} style={{ background: "none", border: "none", color: "#6b7280", fontSize: 13, cursor: "pointer", marginBottom: 16, padding: 0 }}>
              ← Back
            </button>

            <div style={{ display: "flex", marginBottom: 24, background: "#0b0f19", borderRadius: 8, padding: 4 }}>
              {(["Sign In", "Register"] as const).map((label, i) => {
                const active = i === 0 ? isLogin : !isLogin;
                return (
                  <button key={label} onClick={() => setIsLogin(i === 0)}
                    style={{ flex: 1, padding: "6px 0", borderRadius: 6, border: "none", cursor: "pointer", fontWeight: 600, fontSize: 13, background: active ? "#1f2937" : "transparent", color: active ? "#f9fafb" : "#6b7280" }}>
                    {label}
                  </button>
                );
              })}
            </div>

            <form onSubmit={submitEmail} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="Email address"
                required
                style={{ background: "#0b0f19", border: "1px solid rgba(255,255,255,0.08)", color: "#f9fafb", borderRadius: 8, padding: "10px 14px", fontSize: 14, outline: "none" }}
              />
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Password"
                required
                style={{ background: "#0b0f19", border: "1px solid rgba(255,255,255,0.08)", color: "#f9fafb", borderRadius: 8, padding: "10px 14px", fontSize: 14, outline: "none" }}
              />
              {error && <p style={{ color: "#ef4444", fontSize: 13, margin: 0 }}>{error}</p>}
              <button type="submit" disabled={loading}
                style={{ background: "#6366f1", color: "#fff", border: "none", borderRadius: 8, padding: "11px 0", fontWeight: 600, fontSize: 14, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1, marginTop: 4 }}>
                {loading ? "..." : isLogin ? "Sign In" : "Create Account"}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

function GitHubIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.385-1.335-1.755-1.335-1.755-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12c0-6.63-5.37-12-12-12z" />
    </svg>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
    </svg>
  );
}
