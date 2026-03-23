import { useState, useEffect, useRef } from "react";
import { API_BASE } from "../../api/client";

const BASE = `${API_BASE}/api/v1`;

interface Props {
  onAuth: (token: string, emailOrUser: string, avatar: string) => void;
  onClose: () => void;
}

function parseError(data: unknown): string {
  if (typeof data === "string") return data;
  if (data && typeof data === "object") {
    const d = data as Record<string, unknown>;
    if (typeof d.detail === "string") return d.detail;
    if (Array.isArray(d.detail) && d.detail[0]?.msg) return d.detail[0].msg;
  }
  return "Something went wrong";
}

function passwordStrength(pw: string): { score: number; label: string; color: string } {
  let score = 0;
  if (pw.length >= 8) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  const levels = [
    { label: "", color: "transparent" },
    { label: "Weak", color: "#ef4444" },
    { label: "Fair", color: "#f59e0b" },
    { label: "Good", color: "#3b82f6" },
    { label: "Strong", color: "#22c55e" },
  ];
  return { score, ...levels[score] };
}

function EyeIcon({ open }: { open: boolean }) {
  return open ? (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  ) : (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  );
}

function FieldWrapper({ children }: { children: React.ReactNode }) {
  return <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>{children}</div>;
}

function Label({ text, htmlFor }: { text: string; htmlFor: string }) {
  return <label htmlFor={htmlFor} style={{ color: "#9ca3af", fontSize: 12, fontWeight: 500, letterSpacing: "0.03em" }}>{text}</label>;
}

function PasswordField({
  value, onChange, placeholder, label, id,
}: { value: string; onChange: (v: string) => void; placeholder: string; label: string; id: string }) {
  const [show, setShow] = useState(false);
  const [focused, setFocused] = useState(false);
  return (
    <FieldWrapper>
      <Label text={label} htmlFor={id} />
      <div style={{ position: "relative" }}>
        <input
          id={id}
          type={show ? "text" : "password"}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          required
          maxLength={72}
          style={{
            width: "100%", background: "rgba(255,255,255,0.04)",
            border: `1px solid ${focused ? "rgba(99,102,241,0.6)" : "rgba(255,255,255,0.08)"}`,
            color: "#f9fafb", borderRadius: 10, padding: "11px 42px 11px 14px",
            fontSize: 14, outline: "none", boxSizing: "border-box", transition: "border-color 0.15s",
          }}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
        />
        <button
          type="button"
          onClick={() => setShow(s => !s)}
          style={{
            position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)",
            background: "none", border: "none", color: "#6b7280", cursor: "pointer",
            padding: 0, display: "flex", alignItems: "center",
          }}
          tabIndex={-1}
        >
          <EyeIcon open={show} />
        </button>
      </div>
    </FieldWrapper>
  );
}

export default function AuthModal({ onAuth, onClose }: Props) {
  const [tab, setTab] = useState<"login" | "register">("login");
  const [mode, setMode] = useState<"options" | "email" | "pending">("options");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);

  // Focus trap: keep Tab/Shift+Tab inside the dialog
  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;
    const focusable = 'button, [href], input, textarea, select, [tabindex]:not([tabindex="-1"])';
    const nodes = () => Array.from(el.querySelectorAll<HTMLElement>(focusable)).filter(n => !n.hasAttribute("disabled"));
    // Move focus into the dialog on open
    nodes()[0]?.focus();
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") { onClose(); return; }
      if (e.key !== "Tab") return;
      const items = nodes();
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) { e.preventDefault(); last.focus(); }
      } else {
        if (document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [mode, onClose]);

  const titleId = "auth-modal-title";
  const strength = passwordStrength(password);

  function switchTab(t: "login" | "register") {
    setTab(t);
    setError("");
    setPassword("");
    setConfirmPassword("");
  }

  async function submitEmail(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (tab === "register" && password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      const body: Record<string, string> = { email, password };
      const res = await fetch(`${BASE}/auth/${tab}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(parseError(data));
      if (tab === "register") { setMode("pending"); return; }
      onAuth(data.access_token, data.email ?? email, data.avatar_url ?? "");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  const overlay: React.CSSProperties = {
    position: "fixed", inset: 0, background: "rgba(0,0,0,0.65)",
    display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50,
    backdropFilter: "blur(6px)",
  };
  const card: React.CSSProperties = {
    background: "#0f1117", border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 20, padding: "40px 36px", width: 420, maxWidth: "calc(100vw - 32px)", position: "relative",
    boxShadow: "0 24px 64px rgba(0,0,0,0.6)",
  };
  const providerBtn: React.CSSProperties = {
    width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: 10,
    background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 10, padding: "12px 16px", color: "#f9fafb", fontSize: 14,
    fontWeight: 500, cursor: "pointer", transition: "background 0.15s",
  };
  const closeBtn: React.CSSProperties = {
    position: "absolute", top: 16, right: 18, background: "none", border: "none",
    color: "#4b5563", fontSize: 18, cursor: "pointer", lineHeight: 1,
  };

  if (mode === "pending") {
    return (
      <div style={overlay} onClick={onClose} role="presentation">
        <div
          ref={dialogRef}
          style={card}
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          onClick={e => e.stopPropagation()}
        >
          <button onClick={onClose} style={closeBtn} aria-label="Close dialog">✕</button>
          <div style={{ textAlign: "center", padding: "8px 0" }}>
            <div style={{ fontSize: 44, marginBottom: 16 }}>📬</div>
            <p id={titleId} style={{ color: "#f9fafb", fontSize: 18, fontWeight: 700, marginBottom: 10 }}>Check your inbox</p>
            <p style={{ color: "#6b7280", fontSize: 14, lineHeight: 1.7 }}>
              We sent a verification link to<br />
              <strong style={{ color: "#a5b4fc" }}>{email}</strong>
            </p>
            <p style={{ color: "#4b5563", fontSize: 13, marginTop: 20 }}>
              Didn't get it? Check your spam folder, or submit the form again to resend.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (mode === "options") {
    return (
      <div style={overlay} onClick={onClose} role="presentation">
        <div
          ref={dialogRef}
          style={card}
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          onClick={e => e.stopPropagation()}
        >
          <button onClick={onClose} style={closeBtn} aria-label="Close dialog">✕</button>
          <h2 id={titleId} style={{ color: "#f9fafb", fontWeight: 700, fontSize: 22, marginBottom: 6 }}>Welcome to Debugger</h2>
          <p style={{ color: "#6b7280", fontSize: 14, marginBottom: 28 }}>Sign in to save your progress.</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <button style={providerBtn} onClick={() => {
              window.location.href = `${API_BASE}/api/v1/auth/github`;
            }}
              onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.08)")}
              onMouseLeave={e => (e.currentTarget.style.background = "rgba(255,255,255,0.04)")}>
              <GitHubIcon /> Continue with GitHub
            </button>
            <button style={providerBtn} onClick={() => {
              window.location.href = `${API_BASE}/api/v1/auth/google`;
            }}
              onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.08)")}
              onMouseLeave={e => (e.currentTarget.style.background = "rgba(255,255,255,0.04)")}>
              <GoogleIcon /> Continue with Google
            </button>
            <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "6px 0" }}>
              <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.06)" }} />
              <span style={{ color: "#374151", fontSize: 12 }}>or continue with email</span>
              <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.06)" }} />
            </div>
            <button style={{ ...providerBtn, justifyContent: "center" }} onClick={() => setMode("email")}
              onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.08)")}
              onMouseLeave={e => (e.currentTarget.style.background = "rgba(255,255,255,0.04)")}>
              Continue with Email
            </button>
          </div>
          <p style={{ color: "#374151", fontSize: 12, textAlign: "center", marginTop: 24 }}>
            By continuing you agree to our Terms and Privacy Policy.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={overlay} onClick={onClose} role="presentation">
      <div
        ref={dialogRef}
        style={card}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={e => e.stopPropagation()}
      >
        <button onClick={onClose} style={closeBtn} aria-label="Close dialog">✕</button>

        <button onClick={() => setMode("options")} style={{ background: "none", border: "none", color: "#6b7280", fontSize: 13, cursor: "pointer", padding: 0, marginBottom: 20, display: "flex", alignItems: "center", gap: 6 }}>
          ← Back
        </button>

        <h2 id={titleId} style={{ color: "#f9fafb", fontWeight: 700, fontSize: 20, marginBottom: 4 }}>
          {tab === "login" ? "Sign in" : "Create account"}
        </h2>
        <p style={{ color: "#6b7280", fontSize: 13, marginBottom: 24 }}>
          {tab === "login" ? "Welcome back." : "Start debugging smarter."}
        </p>

        <div style={{ display: "flex", marginBottom: 28, background: "rgba(255,255,255,0.03)", borderRadius: 10, padding: 4 }}>
          {(["login", "register"] as const).map((t) => (
            <button key={t} onClick={() => switchTab(t)}
              style={{ flex: 1, padding: "8px 0", borderRadius: 8, border: "none", cursor: "pointer", fontWeight: 600, fontSize: 13, transition: "all 0.15s", background: tab === t ? "#1f2937" : "transparent", color: tab === t ? "#f9fafb" : "#4b5563" }}>
              {t === "login" ? "Sign In" : "Register"}
            </button>
          ))}
        </div>

        <form onSubmit={submitEmail} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <FieldWrapper>
            <Label text="Email address" htmlFor="auth-email" />
            <input
              id="auth-email"
              type="email" value={email} onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com" required
              style={{
                width: "100%", background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)", color: "#f9fafb",
                borderRadius: 10, padding: "11px 14px", fontSize: 14, outline: "none",
                boxSizing: "border-box", transition: "border-color 0.15s",
              }}
              onFocus={e => (e.currentTarget.style.borderColor = "rgba(99,102,241,0.6)")}
              onBlur={e => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)")}
            />
          </FieldWrapper>

          <PasswordField value={password} onChange={setPassword} placeholder="••••••••" label="Password" id="auth-password" />

          {tab === "register" && password.length > 0 && (
            <div style={{ marginTop: -6 }}>
              <div style={{ display: "flex", gap: 4, marginBottom: 4 }}>
                {[1, 2, 3, 4].map(i => (
                  <div key={i} style={{
                    flex: 1, height: 3, borderRadius: 2,
                    background: i <= strength.score ? strength.color : "rgba(255,255,255,0.08)",
                    transition: "background 0.2s",
                  }} />
                ))}
              </div>
              {strength.label && (
                <span style={{ fontSize: 11, color: strength.color }}>{strength.label} password</span>
              )}
            </div>
          )}

          {tab === "register" && (
            <PasswordField value={confirmPassword} onChange={setConfirmPassword} placeholder="••••••••" label="Confirm password" id="auth-confirm-password" />
          )}

          {error && (
            <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 8, padding: "10px 12px", color: "#f87171", fontSize: 13 }}>
              {error}
            </div>
          )}

          <button type="submit" disabled={loading} style={{
            background: loading ? "rgba(99,102,241,0.5)" : "#6366f1", color: "#fff", border: "none",
            borderRadius: 10, padding: "13px 0", fontWeight: 600, fontSize: 14,
            cursor: loading ? "not-allowed" : "pointer", marginTop: 4, transition: "background 0.15s",
            display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
          }}>
            {loading ? <Spinner /> : null}
            {loading ? "Please wait…" : tab === "login" ? "Sign In" : "Create Account"}
          </button>
        </form>
      </div>
    </div>
  );
}

function Spinner() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ animation: "spin 0.7s linear infinite" }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
    </svg>
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
