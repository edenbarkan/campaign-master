import React, { useState } from "react";

import RoleHeader from "../components/RoleHeader.jsx";
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
      if (!payload.filled) {
        const reason = payload.reason || "NO_ELIGIBLE_ADS";
        const message =
          reason === "FREQ_CAP"
            ? "Frequency cap hit. Try again in a minute or change filters."
            : "No fill available. Try adjusting category, geo, placement, or device.";
        setError(message);
        setAssignment(null);
        return;
      }
      setAssignment(payload);
      localStorage.setItem("partnerLatestAd", JSON.stringify(payload));
    } catch (err) {
      setError("Unable to request an ad. Check your connection and try again.");
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
        <RoleHeader
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
                <div className="card subtle">
                  <h3>Why this ad?</h3>
                  <p className="muted">{assignment.explanation}</p>
                  {assignment.score_breakdown ? (
                    <div className="table compact">
                      {[
                        ["Profit", assignment.score_breakdown.profit],
                        [
                          "Smoothed CTR",
                          `${((assignment.score_breakdown.ctr || 0) * 100).toFixed(2)}%`
                        ],
                        ["CTR weight", assignment.score_breakdown.ctr_weight],
                        ["Targeting bonus", assignment.score_breakdown.targeting_bonus],
                        [
                          "Partner reject rate",
                          `${(
                            (assignment.score_breakdown.partner_reject_rate || 0) * 100
                          ).toFixed(2)}%`
                        ],
                        [
                          "Partner quality penalty",
                          assignment.score_breakdown.partner_reject_penalty
                        ],
                        ["Total score", assignment.score_breakdown.total]
                      ].map(([label, value]) => (
                        <div className="table-row compact" key={label}>
                          <span className="muted">{label}</span>
                          <span>{value}</span>
                        </div>
                      ))}
                    </div>
                  ) : null}
                  <details className="score-legend">
                    <summary>What do these numbers mean?</summary>
                    <ul className="legend-list">
                      <li>
                        <strong>Profit</strong> — Expected profit for this impression.
                      </li>
                      <li>
                        <strong>Smoothed CTR</strong> — Recent click-through rate estimate.
                      </li>
                      <li>
                        <strong>CTR weight</strong> — How strongly CTR influences final score.
                      </li>
                      <li>
                        <strong>Targeting bonus</strong> — Extra score for matching partner
                        targeting.
                      </li>
                      <li>
                        <strong>Partner reject rate</strong> — Partner’s recent rejected-click
                        ratio.
                      </li>
                      <li>
                        <strong>Partner quality penalty</strong> — Score reduction caused by
                        partner reject rate.
                      </li>
                      <li>
                        <strong>Total score</strong> — Final ranking score used by the matcher.
                      </li>
                    </ul>
                  </details>
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
