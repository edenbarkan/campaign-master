import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import BuyerHeader from "../components/BuyerHeader.jsx";
import { useAuth } from "../contexts/AuthContext";
import { apiFetch } from "../lib/api";

const emptyForm = {
  name: "",
  status: "active",
  budget_total: "",
  buyer_cpc: "",
  partner_payout: "",
  targeting_category: "",
  targeting_geo: "",
  start_date: "",
  end_date: ""
};

const BuyerHome = () => {
  const { user, token } = useAuth();
  const [campaigns, setCampaigns] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadCampaigns = async () => {
    try {
      const payload = await apiFetch("/buyer/campaigns", { token });
      setCampaigns(payload.campaigns || []);
    } catch (err) {
      setError("Unable to load campaigns.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!token) return;
    loadCampaigns();
  }, [token]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    const buyerCpc = Number(form.buyer_cpc);
    const partnerPayout = Number(form.partner_payout);

    if (Number.isNaN(buyerCpc) || Number.isNaN(partnerPayout)) {
      setError("Enter numeric pricing values.");
      return;
    }

    if (buyerCpc < partnerPayout) {
      setError("Partner payout cannot exceed buyer CPC.");
      return;
    }

    const payload = {
      name: form.name,
      status: form.status,
      budget_total: Number(form.budget_total),
      buyer_cpc: buyerCpc,
      partner_payout: partnerPayout,
      targeting: {
        category: form.targeting_category || null,
        geo: form.targeting_geo || null
      },
      start_date: form.start_date || null,
      end_date: form.end_date || null
    };

    try {
      if (editingId) {
        await apiFetch(`/buyer/campaigns/${editingId}`, {
          method: "PUT",
          body: payload,
          token
        });
      } else {
        await apiFetch("/buyer/campaigns", {
          method: "POST",
          body: payload,
          token
        });
      }
      setForm(emptyForm);
      setEditingId(null);
      loadCampaigns();
    } catch (err) {
      setError("Unable to save campaign. Check the fields and try again.");
    }
  };

  const handleEdit = (campaign) => {
    setEditingId(campaign.id);
    setForm({
      name: campaign.name,
      status: campaign.status,
      budget_total: campaign.budget_total,
      buyer_cpc: campaign.buyer_cpc,
      partner_payout: campaign.partner_payout,
      targeting_category: campaign.targeting?.category || "",
      targeting_geo: campaign.targeting?.geo || "",
      start_date: campaign.start_date || "",
      end_date: campaign.end_date || ""
    });
  };

  const handleReset = () => {
    setEditingId(null);
    setForm(emptyForm);
    setError("");
  };

  return (
    <main className="page dashboard">
      <section className="panel">
        <BuyerHeader
          title={`Hello, ${user?.email}`}
          subtitle="Launch campaigns and manage pricing."
        />
        <div className="grid">
          <section className="card">
            <h2>{editingId ? "Edit campaign" : "New campaign"}</h2>
            <form className="form" onSubmit={handleSubmit}>
              <label className="field">
                <span>Name</span>
                <input
                  name="name"
                  value={form.name}
                  onChange={handleChange}
                  placeholder="Spring push"
                  required
                />
              </label>
              <label className="field">
                <span>Status</span>
                <select name="status" value={form.status} onChange={handleChange}>
                  <option value="active">Active</option>
                  <option value="paused">Paused</option>
                </select>
              </label>
              <div className="field-row">
                <label className="field">
                  <span>Total budget</span>
                  <input
                    name="budget_total"
                    type="number"
                    step="0.01"
                    value={form.budget_total}
                    onChange={handleChange}
                    placeholder="1200"
                    required
                  />
                </label>
                <label className="field">
                  <span>Buyer CPC</span>
                  <input
                    name="buyer_cpc"
                    type="number"
                    step="0.01"
                    value={form.buyer_cpc}
                    onChange={handleChange}
                    placeholder="2.50"
                    required
                  />
                </label>
              </div>
              <label className="field">
                <span>Partner payout (CPC)</span>
                <input
                  name="partner_payout"
                  type="number"
                  step="0.01"
                  value={form.partner_payout}
                  onChange={handleChange}
                  placeholder="1.50"
                  required
                />
              </label>
              <div className="field-row">
                <label className="field">
                  <span>Targeting category</span>
                  <input
                    name="targeting_category"
                    value={form.targeting_category}
                    onChange={handleChange}
                    placeholder="Fitness"
                  />
                </label>
                <label className="field">
                  <span>Targeting geo</span>
                  <input
                    name="targeting_geo"
                    value={form.targeting_geo}
                    onChange={handleChange}
                    placeholder="US"
                  />
                </label>
              </div>
              <div className="field-row">
                <label className="field">
                  <span>Start date</span>
                  <input
                    name="start_date"
                    type="date"
                    value={form.start_date}
                    onChange={handleChange}
                  />
                </label>
                <label className="field">
                  <span>End date</span>
                  <input
                    name="end_date"
                    type="date"
                    value={form.end_date}
                    onChange={handleChange}
                  />
                </label>
              </div>
              {error ? <p className="error">{error}</p> : null}
              <div className="actions">
                <button className="button primary" type="submit">
                  {editingId ? "Update campaign" : "Create campaign"}
                </button>
                {editingId ? (
                  <button className="button ghost" type="button" onClick={handleReset}>
                    Cancel
                  </button>
                ) : null}
              </div>
            </form>
          </section>
          <section className="card">
            <h2>Campaigns</h2>
            {loading ? <p className="muted">Loading campaigns...</p> : null}
            {!loading && campaigns.length === 0 ? (
              <p className="muted">No campaigns yet. Create the first one.</p>
            ) : null}
            <div className="table">
              {campaigns.map((campaign) => (
                <div className="table-row" key={campaign.id}>
                  <div>
                    <p className="row-title">{campaign.name}</p>
                    <p className="muted">
                      {campaign.status} · ${campaign.buyer_cpc.toFixed(2)} CPC
                    </p>
                  </div>
                  <div className="row-metrics">
                    <span>${campaign.budget_spent.toFixed(2)} spent</span>
                    <span>${campaign.budget_remaining.toFixed(2)} left</span>
                  </div>
                  <button
                    className="button ghost"
                    type="button"
                    onClick={() => handleEdit(campaign)}
                  >
                    Edit
                  </button>
                  <Link
                    className="button ghost"
                    to={`/buyer/campaigns/${campaign.id}`}
                  >
                    Ads
                  </Link>
                </div>
              ))}
            </div>
          </section>
        </div>
      </section>
    </main>
  );
};

export default BuyerHome;
