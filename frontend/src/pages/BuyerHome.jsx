import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import RoleHeader from "../components/RoleHeader.jsx";
import { useAuth } from "../contexts/AuthContext";
import { apiFetch } from "../lib/api";

const round2 = (value) => {
  if (Number.isNaN(value)) return 0;
  return Math.round((value + Number.EPSILON) * 100) / 100;
};

const computePayout = (maxCpc, feePercent) => {
  const fee = Number(feePercent);
  if (Number.isNaN(maxCpc) || Number.isNaN(fee)) return 0;
  return round2(maxCpc * (1 - fee / 100));
};

const emptyForm = {
  name: "",
  status: "active",
  budget_total: "",
  max_cpc: "",
  targeting_category: "",
  targeting_geo: "",
  targeting_device: "",
  targeting_placement: "",
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
  const [platformFeePercent, setPlatformFeePercent] = useState(30);
  const computedPayout = computePayout(Number(form.max_cpc), platformFeePercent);

  const loadCampaigns = async () => {
    try {
      const payload = await apiFetch("/buyer/campaigns", { token });
      setCampaigns(payload.campaigns || []);
      const metaFee = payload.meta?.platform_fee_percent;
      if (typeof metaFee === "number") {
        setPlatformFeePercent(metaFee);
      } else if (payload.campaigns?.length) {
        const fee = payload.campaigns[0]?.platform_fee_percent;
        if (typeof fee === "number") {
          setPlatformFeePercent(fee);
        }
      }
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

    const maxCpc = Number(form.max_cpc);

    if (Number.isNaN(maxCpc)) {
      setError("Enter a numeric max CPC.");
      return;
    }

    if (maxCpc <= 0) {
      setError("Max CPC must be greater than zero.");
      return;
    }

    const payload = {
      name: form.name,
      status: form.status,
      budget_total: Number(form.budget_total),
      max_cpc: maxCpc,
      targeting: {
        category: form.targeting_category || null,
        geo: form.targeting_geo || null,
        device: form.targeting_device || null,
        placement: form.targeting_placement || null
      },
      start_date: form.start_date || null,
      end_date: form.end_date || null
    };

    try {
      if (editingId) {
        const response = await apiFetch(`/buyer/campaigns/${editingId}`, {
          method: "PUT",
          body: payload,
          token
        });
        if (typeof response.campaign?.platform_fee_percent === "number") {
          setPlatformFeePercent(response.campaign.platform_fee_percent);
        }
      } else {
        const response = await apiFetch("/buyer/campaigns", {
          method: "POST",
          body: payload,
          token
        });
        if (typeof response.campaign?.platform_fee_percent === "number") {
          setPlatformFeePercent(response.campaign.platform_fee_percent);
        }
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
      max_cpc: campaign.max_cpc ?? campaign.buyer_cpc,
      targeting_category: campaign.targeting?.category || "",
      targeting_geo: campaign.targeting?.geo || "",
      targeting_device: campaign.targeting?.device || "",
      targeting_placement: campaign.targeting?.placement || "",
      start_date: campaign.start_date || "",
      end_date: campaign.end_date || ""
    });
    if (typeof campaign.platform_fee_percent === "number") {
      setPlatformFeePercent(campaign.platform_fee_percent);
    }
  };

  const handleReset = () => {
    setEditingId(null);
    setForm(emptyForm);
    setError("");
  };

  return (
    <main className="page dashboard">
      <section className="panel">
        <RoleHeader
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
                  <span>Max CPC</span>
                  <input
                    name="max_cpc"
                    type="number"
                    step="0.01"
                    value={form.max_cpc}
                    onChange={handleChange}
                    placeholder="2.50"
                    required
                  />
                </label>
              </div>
              <div className="field-row">
                <label className="field">
                  <span>Platform fee</span>
                  <input
                    value={`${platformFeePercent}%`}
                    readOnly
                  />
                </label>
                <label className="field">
                  <span>Partner payout (computed)</span>
                  <input
                    value={`$${computedPayout.toFixed(2)}`}
                    readOnly
                  />
                </label>
              </div>
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
                  <span>Targeting device</span>
                  <input
                    name="targeting_device"
                    value={form.targeting_device}
                    onChange={handleChange}
                    placeholder="Mobile"
                  />
                </label>
                <label className="field">
                  <span>Targeting placement</span>
                  <input
                    name="targeting_placement"
                    value={form.targeting_placement}
                    onChange={handleChange}
                    placeholder="Sidebar"
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
                      {campaign.status} · $
                      {(campaign.max_cpc ?? campaign.buyer_cpc).toFixed(2)} max CPC
                    </p>
                    {campaign.delivery_status ? (
                      <span className={`badge ${campaign.delivery_status.toLowerCase()}`}>
                        {campaign.delivery_status.replace("_", " ")}
                      </span>
                    ) : null}
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
