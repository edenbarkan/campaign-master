export const GLOSSARY = [
  {
    term: "Max CPC",
    definition: "The highest amount a buyer pays for a single accepted click."
  },
  {
    term: "Partner payout",
    definition: "What a partner earns per accepted click."
  },
  {
    term: "Platform fee",
    definition: "The share kept by the platform from the buyer’s max CPC."
  },
  {
    term: "Fill rate",
    definition: "The percent of ad requests that return an ad."
  },
  {
    term: "Smoothed CTR",
    definition: "A stabilized click-through estimate based on recent data."
  },
  {
    term: "Targeting bonus",
    definition: "A ranking boost when requested targeting matches campaign settings."
  },
  {
    term: "Partner reject rate",
    definition: "The partner’s rejected-click ratio over the lookback window."
  },
  {
    term: "Partner quality penalty",
    definition: "A ranking reduction based on partner reject rate and quality state."
  },
  {
    term: "Market Stability Guard",
    definition: "Adaptive scoring layer that stabilizes delivery quality (ranking only)."
  },
  {
    term: "Frequency cap",
    definition: "Prevents showing the same ad to the same partner too often."
  }
];

export const HOW_IT_WORKS = {
  buyer: {
    title: "How it works for buyers",
    summary: [
      "Create a campaign with budget + max CPC.",
      "Add ads with image + destination URL.",
      "Campaign status controls delivery.",
      "Spend is charged only on accepted clicks."
    ],
    examples: [
      "Example: Max CPC $2.00 means you’ll never pay more than $2.00 per accepted click.",
      "Example: Paused campaigns won’t serve even if budget remains."
    ],
    neverChanges: [
      "Scoring affects ranking only — billing rules remain the same.",
      "Rejected clicks never charge and never pay out."
    ],
    questions: [
      {
        q: "Why did my campaign get no fill?",
        a: "No eligible ads matched targeting, budget, or frequency caps at request time."
      },
      {
        q: "Why is there a partner penalty in scoring?",
        a: "Partner quality is partner-derived; it never changes your billing."
      },
      {
        q: "How do I improve delivery?",
        a: "Increase budget, relax targeting, and keep ads active."
      }
    ]
  },
  partner: {
    title: "How it works for partners",
    summary: [
      "Request an ad and place the tracking link on your site.",
      "Record impressions to keep CTR accurate.",
      "You earn per accepted click.",
      "Quality signals protect the marketplace."
    ],
    examples: [
      "Example: Use /t/<code> tracking URLs for clicks.",
      "Example: Recording impressions improves CTR accuracy."
    ],
    neverChanges: [
      "Scoring affects ranking only — billing rules remain the same.",
      "Rejected clicks never charge and never pay out."
    ],
    questions: [
      {
        q: "Why do I see no fill?",
        a: "Requests can be unfilled if targeting, budget, or frequency caps block delivery."
      },
      {
        q: "Why do I see a penalty?",
        a: "Penalties are partner-derived quality signals, not ad-specific."
      },
      {
        q: "How do I improve partner quality?",
        a: "Avoid repeated clicks, rate spikes, and ensure clean user-agent headers."
      }
    ]
  },
  admin: {
    title: "How it works for admins",
    summary: [
      "Monitor marketplace health and risk trends.",
      "Reject reasons highlight traffic quality issues.",
      "Fill rate and take rate show marketplace balance.",
      "Scoring only changes ranking — billing stays consistent."
    ],
    examples: [
      "Example: A reject spike may indicate a traffic burst from one partner.",
      "Example: Low fill rate can signal tight supply or aggressive targeting."
    ],
    neverChanges: [
      "Scoring affects ranking only — billing rules remain the same.",
      "Rejected clicks never charge and never pay out."
    ],
    questions: [
      {
        q: "Why does no-fill happen?",
        a: "Eligible supply can be constrained by budgets, caps, or targeting."
      },
      {
        q: "Why do I see a penalty?",
        a: "Penalties are partner-derived quality signals that adjust ranking only."
      },
      {
        q: "What should I do when rejection spikes?",
        a: "Inspect top reasons, review partner traffic sources, and throttle bursts."
      }
    ]
  }
};
