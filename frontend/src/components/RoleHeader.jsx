import React from "react";

import { useAuth } from "../contexts/AuthContext";
import AdminHeader from "./AdminHeader.jsx";
import BuyerHeader from "./BuyerHeader.jsx";
import PartnerHeader from "./PartnerHeader.jsx";

const RoleHeader = ({ title, subtitle }) => {
  const { user } = useAuth();
  const role = user?.role;

  if (role === "ADMIN") {
    return <AdminHeader title={title} subtitle={subtitle} />;
  }
  if (role === "BUYER") {
    return <BuyerHeader title={title} subtitle={subtitle} />;
  }
  if (role === "PARTNER") {
    return <PartnerHeader title={title} subtitle={subtitle} />;
  }

  return null;
};

export default RoleHeader;
