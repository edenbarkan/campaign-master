import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import BuyerHeader from "../components/BuyerHeader.jsx";
import { useAuth } from "../contexts/AuthContext";
import { apiFetch } from "../lib/api";

const emptyAd = {
  title: "",
  body: "",
  image_url: "",
  destination_url: "",
  active: true
};

const CampaignDetailPage = () => {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const { token } = useAuth();
  const [campaign, setCampaign] = useState(null);
  const [ads, setAds] = useState([]);
  const [form, setForm] = useState(emptyAd);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const loadCampaign = async () => {
    try {
      const payload = await apiFetch(`/buyer/campaigns/${campaignId}`, { token });
      setCampaign(payload.campaign);
    } catch (err) {
      setError("Unable to load campaign.");
    }
  };

  const loadAds = async () => {
    try {
      const payload = await apiFetch(`/buyer/campaigns/${campaignId}/ads`, { token });
      setAds(payload.ads || []);
    } catch (err) {
      setError("Unable to load ads.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!token) return;
    loadCampaign();
    loadAds();
  }, [token, campaignId]);

  const handleChange = (event) => {
    const { name, value, type, checked } = event.target;
    setForm((prev) => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    const payload = {
      title: form.title,
      body: form.body,
      image_url: form.image_url,
      destination_url: form.destination_url,
      active: form.active
    };

    try {
      if (editingId) {
        await apiFetch(`/buyer/campaigns/${campaignId}/ads/${editingId}`, {
          method: "PUT",
          body: payload,
          token
        });
      } else {
        await apiFetch(`/buyer/campaigns/${campaignId}/ads`, {
          method: "POST",
          body: payload,
          token
        });
      }
      setForm(emptyAd);
      setEditingId(null);
      loadAds();
    } catch (err) {
      setError("Unable to save the ad. Check the fields and try again.");
    }
  };

  const handleEdit = (ad) => {
    setEditingId(ad.id);
    setForm({
      title: ad.title,
      body: ad.body,
      image_url: ad.image_url,
      destination_url: ad.destination_url,
      active: ad.active
    });
  };

  const handleReset = () => {
    setEditingId(null);
    setForm(emptyAd);
    setError("");
  };

  return (
    <main className="page dashboard">
      <section className="panel">
        <BuyerHeader
          title={campaign ? campaign.name : "Campaign detail"}
          subtitle="Manage creative assets for this campaign."
        />
        <div className="actions">
          <button className="button ghost" type="button" onClick={() => navigate(-1)}>
            Back
          </button>
        </div>
        <div className="grid">
          <section className="card">
            <h2>{editingId ? "Edit ad" : "New ad"}</h2>
            <form className="form" onSubmit={handleSubmit}>
              <label className="field">
                <span>Headline</span>
                <input
                  name="title"
                  value={form.title}
                  onChange={handleChange}
                  placeholder="Fuel your run"
                  required
                />
              </label>
              <label className="field">
                <span>Body text</span>
                <textarea
                  name="body"
                  value={form.body}
                  onChange={handleChange}
                  placeholder="Lightweight shoes for long-distance comfort."
                  rows={3}
                  required
                />
              </label>
              <label className="field">
                <span>Image URL</span>
                <input
                  name="image_url"
                  value={form.image_url}
                  onChange={handleChange}
                  placeholder="https://..."
                  required
                />
              </label>
              <label className="field">
                <span>Destination URL</span>
                <input
                  name="destination_url"
                  value={form.destination_url}
                  onChange={handleChange}
                  placeholder="https://brand.com/landing"
                  required
                />
              </label>
              <label className="checkbox">
                <input
                  type="checkbox"
                  name="active"
                  checked={form.active}
                  onChange={handleChange}
                />
                <span>Active</span>
              </label>
              {error ? <p className="error">{error}</p> : null}
              <div className="actions">
                <button className="button primary" type="submit">
                  {editingId ? "Update ad" : "Create ad"}
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
            <h2>Ads</h2>
            {loading ? <p className="muted">Loading ads...</p> : null}
            {!loading && ads.length === 0 ? (
              <p className="muted">No ads yet. Add your first creative.</p>
            ) : null}
            <div className="table">
              {ads.map((ad) => (
                <div className="table-row" key={ad.id}>
                  <div>
                    <p className="row-title">{ad.title}</p>
                    <p className="muted">{ad.active ? "Active" : "Paused"}</p>
                  </div>
                  <div className="row-metrics">
                    <span>{ad.image_url}</span>
                    <span>{ad.destination_url}</span>
                  </div>
                  <button className="button ghost" type="button" onClick={() => handleEdit(ad)}>
                    Edit
                  </button>
                </div>
              ))}
            </div>
          </section>
        </div>
      </section>
    </main>
  );
};

export default CampaignDetailPage;
