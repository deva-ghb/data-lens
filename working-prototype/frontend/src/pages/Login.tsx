import { useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { apiSend, ApiError } from "../api/client";
import { PHONE_ROLES, type Me } from "../auth/useMe";
import { DataLensLogo } from "../brand/DataLensLogo";
import { MirsalLogo } from "../brand/MirsalLogo";
import { Button } from "../ui/Button";
import { Field, Input } from "../ui/Field";
import "./login.css";

const ACCOUNTS = [
  ["Planner", "daniel.mensah"],
  ["Shift manager", "khalid.alnuaimi"],
  ["Permit issuer", "priya.raman"],
  ["Head of HSE", "layla.haddad"],
  ["Clinician", "sara.ibrahim"],
  ["Foreman", "joseph.kariuki"],
  ["Worker", "arjun.thapa"],
  ["District authority", "ahmed.alshamsi"],
  ["Administrator", "hessa.almansoori"],
];

export function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const client = useQueryClient();

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const me = await apiSend<Me>("POST", "/api/auth/login", { email, password });
      client.setQueryData(["/api/auth/me"], me);
      navigate(PHONE_ROLES.includes(me.role) ? (me.role === "foreman" ? "/m/foreman" : "/m") : "/");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login">
      <div className="login__panel">
        <div className="login__brand">
          <DataLensLogo size={36} />
        </div>
        <div className="login__intro">
          <h1>Sign in</h1>
          <p className="muted">Workforce risk before the shift, for Mirsal Terminals.</p>
        </div>
        <form className="login__form" onSubmit={submit} noValidate>
          <Field label="Work email">
            {(p) => (
              <Input {...p} type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="firstname.lastname@mirsalterminals.com" />
            )}
          </Field>
          <Field label="Password" error={error ?? undefined}>
            {(p) => (
              <Input {...p} type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} invalid={error !== null} />
            )}
          </Field>
          <Button type="submit" variant="primary" block busy={busy}>
            Sign in
          </Button>
        </form>
        <details className="login__help">
          <summary>Demo accounts</summary>
          <p className="small muted">Every account uses the password welcome@123.</p>
          <ul>
            {ACCOUNTS.map(([role, local]) => (
              <li key={local}>
                <button type="button" className="login__account" onClick={() => setEmail(`${local}@mirsalterminals.com`)}>
                  <span>{role}</span>
                  <span className="muted">{local}@mirsalterminals.com</span>
                </button>
              </li>
            ))}
          </ul>
        </details>
        <footer className="login__org">
          <MirsalLogo size={22} />
          <span className="xsmall muted">All people, places and figures are synthetic.</span>
        </footer>
      </div>
      <div className="login__art" aria-hidden="true">
        <div className="login__grid">
          {["Fit", "Fit with controls", "Reassign today", "Refer"].map((t, i) => (
            <div key={t} className={`login__cell login__cell--${i}`}>{t}</div>
          ))}
        </div>
        <p className="login__quote">An incident happens when an activity's risk meets an unsafe act or condition. Data Lens sees that meeting coming, before the shift.</p>
      </div>
    </div>
  );
}
