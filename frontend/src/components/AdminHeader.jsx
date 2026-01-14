import React from "react";

import { useAuth } from "../contexts/AuthContext";

const AdminHeader = ({ title, subtitle }) => {
  const { user, logout } = useAuth();

  return (
    <header className="panel-header">
      <div>
        <p className="eyebrow">ADMIN WORKSPACE</p>
        <h1>{title || `Welcome, ${user?.email}`}</h1>
        {subtitle ? <p className="subhead">{subtitle}</p> : null}
      </div>
      <button className="button ghost" type="button" onClick={logout}>
        Sign out
      </button>
    </header>
  );
};

export default AdminHeader;
