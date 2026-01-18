import React, { useState } from "react";
import { Link } from "react-router-dom";

import RoleHeader from "../components/RoleHeader.jsx";
import OnboardingOverlay from "../components/OnboardingOverlay.jsx";
import { HOW_IT_WORKS, GLOSSARY } from "../lib/helpContent";
import { safeStorage } from "../lib/storage";
import { UI_STRINGS } from "../lib/strings";

const AdminHowItWorks = () => {
  const content = HOW_IT_WORKS.admin;
  const [showOnboarding, setShowOnboarding] = useState(false);

  const restartOnboarding = () => {
    safeStorage.set("onboarding_admin_dismissed", "0");
    setShowOnboarding(true);
  };

  const dismissOnboarding = () => {
    safeStorage.set("onboarding_admin_dismissed", "1");
    setShowOnboarding(false);
  };

  return (
    <main className="page dashboard">
      <section className="panel">
        <RoleHeader
          title="How it works"
          subtitle={UI_STRINGS.admin.dashboardSubtitle}
        />
        <div className="grid">
          <section className="card help-section">
            <h2>Quick summary</h2>
            <ul className="help-list">
              {content.summary.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
          <section className="card help-section">
            <h2>Examples</h2>
            <ul className="help-list">
              {content.examples.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        </div>
        <section className="card help-section">
          <h2>What never changes</h2>
          <ul className="help-list">
            {content.neverChanges.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
        <section className="card help-section">
          <h2>Quick actions</h2>
          <div className="help-actions">
            <Link className="button primary" to="/admin/dashboard">
              Go to Admin Dashboard
            </Link>
            <button className="button ghost" type="button" onClick={restartOnboarding}>
              {UI_STRINGS.common.restartOnboarding}
            </button>
          </div>
        </section>
        <section className="card help-section">
          <h2>Key terms</h2>
          <div className="table">
            {GLOSSARY.map((item) => (
              <div className="table-row compact" key={item.term}>
                <div>
                  <p className="row-title">{item.term}</p>
                  <p className="muted">{item.definition}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
        <section className="card help-section">
          <h2>Common questions</h2>
          <div className="table">
            {content.questions.map((item) => (
              <div className="table-row compact" key={item.q}>
                <div>
                  <p className="row-title">{item.q}</p>
                  <p className="muted">{item.a}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      </section>
      {showOnboarding ? (
        <OnboardingOverlay role="admin" onDismiss={dismissOnboarding} />
      ) : null}
    </main>
  );
};

export default AdminHowItWorks;
