import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

import { apiFetch } from "../lib/api";

const AuthContext = createContext(null);
const STORAGE_KEY = "cm_token";

const normalizeRole = (role) => (role ? role.toUpperCase() : role);

const normalizeUser = (user) => {
  if (!user) return null;
  return { ...user, role: normalizeRole(user.role) };
};

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_KEY));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(token));

  useEffect(() => {
    let active = true;

    if (!token) {
      setUser(null);
      setLoading(false);
      return () => {};
    }

    setLoading(true);
    apiFetch("/auth/me", { token })
      .then((payload) => {
        if (!active) return;
        setUser(normalizeUser(payload.user));
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setUser(null);
        setToken(null);
        localStorage.removeItem(STORAGE_KEY);
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [token]);

  const login = async (email, password) => {
    const payload = await apiFetch("/auth/login", {
      method: "POST",
      body: { email, password }
    });
    setToken(payload.access_token);
    localStorage.setItem(STORAGE_KEY, payload.access_token);
    const normalized = normalizeUser(payload.user);
    setUser(normalized);
    return normalized;
  };

  const register = async (email, password, role) => {
    const payload = await apiFetch("/auth/register", {
      method: "POST",
      body: { email, password, role }
    });
    setToken(payload.access_token);
    localStorage.setItem(STORAGE_KEY, payload.access_token);
    const normalized = normalizeUser(payload.user);
    setUser(normalized);
    return normalized;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(STORAGE_KEY);
  };

  const value = useMemo(
    () => ({ token, user, loading, login, register, logout }),
    [token, user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => useContext(AuthContext);
