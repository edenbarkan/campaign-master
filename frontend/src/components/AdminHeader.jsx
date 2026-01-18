import React from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../contexts/AuthContext";
import { UI_STRINGS } from "../lib/strings";

const AdminHeader = ({ title, subtitle }) => {
  const { user, logout } = useAuth();
  const links = [
    { to: "/admin/dashboard", label: "Dashboard" },
    { to: "/admin/how-it-works", label: UI_STRINGS.common.howItWorksLabel }
  ];

  return (
    <header className="panel-header">
      <div>
        <p className="eyebrow">ADMIN WORKSPACE</p>
        <h1>{title || `Welcome, ${user?.email}`}</h1>
        {subtitle ? <p className="subhead">{subtitle}</p> : null}
        <nav className="subnav">
          {links.map((link) => (
            <Link key={link.to} to={link.to}>
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

export default AdminHeader;
