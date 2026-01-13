import React from "react";
import { Link, useLocation } from "react-router-dom";

import { useAuth } from "../contexts/AuthContext";

const PartnerHeader = ({ title, subtitle }) => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const links = [
    { to: "/partner/dashboard", label: "Dashboard" },
    { to: "/partner/get-ad", label: "Get Ad" }
  ];

  return (
    <header className="panel-header">
      <div>
        <p className="eyebrow">Partner workspace</p>
        <h1>{title || `Welcome, ${user?.email}`}</h1>
        {subtitle ? <p className="subhead">{subtitle}</p> : null}
        <nav className="subnav">
          {links.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={location.pathname === link.to ? "active" : ""}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
      <button className="button ghost" type="button" onClick={logout}>
        Sign out
      </button>
    </header>
  );
};

export default PartnerHeader;
