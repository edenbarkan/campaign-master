import React, { useState } from "react";

import PartnerHeader from "../components/PartnerHeader.jsx";
import { useAuth } from "../contexts/AuthContext";
import { apiFetch } from "../lib/api";

const PartnerHome = () => {
  const { user, token } = useAuth();
  const [filters, setFilters] = useState({
    category: "",
    geo: "",
    placement: "",
    device: ""
  });
  const [assignment, setAssignment] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFilters((prev) => ({ ...prev, [name]: value }));
  };

  const buildQuery = () => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.append(key, value);
    });
    return params.toString();
  };

  const requestAd = async () => {
    setError("");
    setLoading(true);
    try {
      const query = buildQuery();
      const payload = await apiFetch(`/partner/ad${query ? `?${query}` : ""}`, {
        token
      });
      setAssignment(payload);
    } catch (err) {
      setError("No fill available for the current filters.");
      setAssignment(null);
    } finally {
      setLoading(false);
    }
  };

  const recordImpression = async () => {
    if (!assignment) return;
    try {
      await apiFetch(`/track/impression?code=${assignment.assignment_code}`, {
        method: "POST"
      });
    } catch (err) {
      setError("Unable to record impression.");
    }
  };

  const trackingUrl = assignment
    ? `${window.location.origin}${assignment.tracking_url}`
    : "";

  const embedSnippet = assignment
    ? `<a href="${trackingUrl}" target="_blank" rel="noreferrer"><img src="${assignment.ad.image_url}" alt="${assignment.ad.title}" /></a>`
    : "";

  return (
    <main className="page dashboard">
      <section className="panel">
        <PartnerHeader
          title={`Welcome, ${user?.email}`}
          subtitle="Request a fresh ad and start earning."
        />
        <div className="grid">
          <section className="card">
            <h2>Get an ad</h2>
            <div className="form">
              <label className="field">
                <span>Category</span>
                <input
                  name="category"
                  value={filters.category}
                  onChange={handleChange}
                  placeholder="Fitness"
                />
              </label>
              <label className="field">
                <span>Geo</span>
                <input
                  name="geo"
                  value={filters.geo}
                  onChange={handleChange}
                  placeholder="US"
                />
              </label>
              <label className="field">
                <span>Placement</span>
                <input
                  name="placement"
                  value={filters.placement}
                  onChange={handleChange}
                  placeholder="Sidebar"
                />
              </label>
              <label className="field">
                <span>Device</span>
                <input
                  name="device"
                  value={filters.device}
                  onChange={handleChange}
                  placeholder="Mobile"
                />
              </label>
              <button className="button primary" type="button" onClick={requestAd}>
                {loading ? "Requesting..." : "Request ad"}
              </button>
              {error ? <p className="error">{error}</p> : null}
            </div>
          </section>
          <section className="card">
            <h2>Ad preview</h2>
            {!assignment ? (
              <p className="muted">Request an ad to see the creative.</p>
            ) : (
              <div className="ad-preview">
                <img src={assignment.ad.image_url} alt={assignment.ad.title} />
                <h3>{assignment.ad.title}</h3>
                <p>{assignment.ad.body}</p>
                <div className="actions">
                  <button className="button ghost" type="button" onClick={recordImpression}>
                    Record impression
                  </button>
                  <a className="button primary" href={trackingUrl} target="_blank" rel="noreferrer">
                    Test click
                  </a>
                </div>
                <div className="snippet">
                  <p className="muted">Embed snippet</p>
                  <textarea readOnly value={embedSnippet} rows={3} />
                </div>
              </div>
            )}
          </section>
        </div>
      </section>
    </main>
  );
};

export default PartnerHome;
