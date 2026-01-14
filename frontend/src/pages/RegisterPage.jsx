import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../contexts/AuthContext";

const RegisterPage = () => {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("buyer");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const user = await register(email, password, role);
      if (user.role === "BUYER") {
        navigate("/buyer/dashboard");
      } else {
        navigate("/partner/dashboard");
      }
    } catch (err) {
      setError("Unable to register. Try a different email.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="page auth">
      <section className="auth-card">
        <header>
          <p className="eyebrow">Campaign Master</p>
          <h1>Create your account</h1>
          <p className="subhead">Buyers launch campaigns. Partners earn on clicks.</p>
        </header>
        <form onSubmit={handleSubmit} className="form">
          <label className="field">
            <span>Email</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="partner@publisher.com"
              required
            />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Create a password"
              required
            />
          </label>
          <label className="field">
            <span>Role</span>
            <select value={role} onChange={(event) => setRole(event.target.value)}>
              <option value="buyer">Buyer</option>
              <option value="partner">Partner</option>
            </select>
          </label>
          {error ? <p className="error">{error}</p> : null}
          <button className="button primary" type="submit" disabled={submitting}>
            {submitting ? "Creating..." : "Create account"}
          </button>
        </form>
        <p className="muted">
          Already have access? <Link to="/login">Sign in</Link>
        </p>
      </section>
    </main>
  );
};

export default RegisterPage;
