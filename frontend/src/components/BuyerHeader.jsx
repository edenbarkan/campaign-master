import React from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../contexts/AuthContext";

const BuyerHeader = ({ title, subtitle }) => {
  const { user, logout } = useAuth();
  const links = [
    { to: "/buyer/dashboard", label: "Dashboard" },
    { to: "/buyer/campaigns", label: "Campaigns" }
  ];

  return (
    <header className="panel-header">
      <div>
        <p className="eyebrow">BUYER WORKSPACE</p>
        <h1>{title || `Hello, ${user?.email}`}</h1>
        {subtitle ? <p className="subhead">{subtitle}</p> : null}
        <nav className="subnav">
          {links.map((link) => (
            <Link
              key={link.to}
              to={link.to}
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

export default BuyerHeader;
