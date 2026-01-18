import React, { useEffect, useRef } from "react";

import { UI_STRINGS } from "../lib/strings";

const OnboardingOverlay = ({ role, onDismiss }) => {
  const content = UI_STRINGS.onboarding[role];
  const cardRef = useRef(null);
  if (!content) return null;

  useEffect(() => {
    cardRef.current?.focus();
    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        onDismiss?.();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onDismiss]);

  return (
    <div className="onboarding-overlay" role="dialog" aria-modal="true">
      <div className="onboarding-card" tabIndex="-1" ref={cardRef}>
        <p className="eyebrow">Getting started</p>
        <h2>{content.title}</h2>
        <ul>
          {content.steps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ul>
        <div className="onboarding-actions">
          <button className="button primary" type="button" onClick={onDismiss}>
            Got it
          </button>
          <button className="button ghost" type="button" onClick={onDismiss}>
            Skip
          </button>
        </div>
      </div>
    </div>
  );
};

export default OnboardingOverlay;
