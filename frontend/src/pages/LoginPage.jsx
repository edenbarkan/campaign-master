import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../contexts/AuthContext";

const LoginPage = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const user = await login(email, password);
      if (user.role === "BUYER") {
        navigate("/buyer/dashboard");
      } else if (user.role === "PARTNER") {
        navigate("/partner/dashboard");
      } else {
        navigate("/admin/dashboard");
      }
    } catch (err) {
      setError("Unable to sign in. Check your details and try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="page auth">
      <section className="auth-card">
        <header>
          <p className="eyebrow">Campaign Master</p>
          <h1>Welcome back</h1>
          <p className="subhead">
            Campaign Master is an ads marketplace connecting Buyers and Partners.
          </p>
          <div className="trust-bullets">
            <span>Accepted-only billing (no hidden fees)</span>
            <span>Scoring affects ranking only</span>
            <span>Transparent partner payouts</span>
          </div>
        </header>
        <form onSubmit={handleSubmit} className="form">
          <label className="field">
            <span>Email</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="buyer@brand.com"
              required
            />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              required
            />
          </label>
          {error ? <p className="error">{error}</p> : null}
          <button className="button primary" type="submit" disabled={submitting}>
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
        <p className="muted">
          New here? <Link to="/register">Create an account</Link>
        </p>
      </section>
    </main>
  );
};

export default LoginPage;
