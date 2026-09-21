# Fraud Detection Model Information

## 1. Recommended Modeling Strategy

Use a layered ensemble rather than one model. Fraud is rare, labels are delayed, and new attack patterns may not resemble historical fraud.

The recommended starting stack is:

1. **Policy and rules layer:** deterministic controls for known, high-confidence conditions.
2. **Supervised risk model:** gradient-boosted decision trees for transactions with historical labels.
3. **Anomaly model:** detects unusual behavior when labels are missing or fraud patterns are new.
4. **Entity and graph signals:** identifies shared devices, accounts, addresses, payment instruments, and IP clusters.
5. **Decision calibration layer:** converts evidence into a risk score and action threshold.

This combination is practical for a hackathon because it is explainable, performs well on tabular data, and still addresses previously unseen behavior.

## 2. Primary Model Choice

### Recommended: LightGBM or XGBoost

Use LightGBM or XGBoost as the primary supervised classifier. Both handle mixed tabular features, nonlinear relationships, missing values, and feature interactions better than a basic linear model.

Use a binary classifier when reliable fraud labels exist. If labels are sparse or delayed, start with a ranking objective or a class-weighted binary objective and calibrate the resulting probabilities.

Recommended baseline configuration:

- Class weighting or controlled negative sampling for extreme imbalance.
- Time-based train, validation, and test splits.
- Early stopping and conservative tree depth to limit overfitting.
- Probability calibration using Platt scaling or isotonic regression.
- SHAP values or native feature attribution for explanations.

### Why not use a deep neural network first?

Deep models can help with sequences, text, images, and very large datasets, but they increase data, serving, explanation, and maintenance requirements. They are better considered after a strong tabular baseline and reliable labels are available.

## 2A. Hackathon Implementation Recommendation

Use a two-stage implementation so the demo remains reliable.

### Stage 1: Deterministic baseline

Implement transparent rules and a small synthetic dataset first. This ensures the API can always return a meaningful decision when the model is unavailable. Example rules include excessive applications per hour, a new device combined with an identity mismatch, and a payment instrument shared by many accounts.

### Stage 2: Machine-learning enhancement

Train a class-weighted LightGBM or XGBoost classifier on the same feature schema. Compare it with the rule-only baseline using time-based validation. Add an Isolation Forest score for unusual combinations, then calibrate the final risk score and connect it to the same decision policy.

For a hackathon, this is preferable to claiming a complex self-learning system without enough trustworthy historical data. The prototype can demonstrate the feedback loop while clearly labeling synthetic or simulated outcomes.

## 2B. Model Input and Output Contract

The model service should accept a versioned feature payload containing an application reference, hashed customer reference, event timestamp, feature values, and feature schema version. It should return supervised, anomaly, graph, and combined risk scores, reason codes, model version, and top explanation contributions.

The model service should not directly decide whether to approve or decline. Keeping `risk scoring` separate from `decision policy` makes thresholds auditable and allows policy changes without retraining.

## 3. Supporting Models

### 3.1 Anomaly detection

Use Isolation Forest, Local Outlier Factor, or an autoencoder to identify unusual behavior. Train primarily on trusted or mostly legitimate historical behavior. Anomaly scores should be treated as supporting evidence, not as an automatic decline reason.

Useful for:

- New fraud campaigns.
- Sudden changes in customer behavior.
- Rare combinations that supervised models have not seen.
- Cold-start cases with limited history.

### 3.2 Graph-based risk signals

Represent relationships between customers, devices, phone numbers, addresses, bank accounts, cards, IP addresses, and applications. Start with simple graph features before using a graph neural network.

Examples:

- Number of customers sharing a device.
- Number of applications linked to one payment account.
- Fraud rate among neighboring entities.
- Distance from a known fraudulent entity.
- Size and density of a connected component.

### 3.3 Sequence and behavioral model

For a later iteration, use a sequence model or time-window embedding to represent click, login, application, and device behavior. This should be evaluated only after event ordering, identity resolution, and sequence labels are trustworthy.

## 4. Feature Catalog

### 4.1 Identity and application features

- Identity verification result and confidence.
- Name, date-of-birth, address, phone, and email consistency.
- Age of phone number, email, and address where legally permitted.
- Number of applications submitted in the last 1 hour, 24 hours, and 7 days.
- Time from registration to application.
- Reuse of personal information across applications.
- Loan amount relative to historical behavior or declared income.

### 4.2 Device and network features

- New-device indicator and device age.
- Number of accounts using the same device.
- Emulator, rooted-device, automation, or tampering signal.
- IP reputation and number of accounts per IP.
- VPN, proxy, hosting-provider, and Tor indicators where available.
- Geographic distance from recent activity.
- Impossible travel or rapid location changes.

### 4.3 Behavioral features

- Time spent on application sections.
- Typing, navigation, and correction patterns where consent and policy allow.
- Copy-paste or automation indicators.
- Login time-of-day deviation from the customer baseline.
- Sudden change in device, location, channel, or session behavior.
- Failed login, OTP, password reset, and document-upload velocity.

### 4.4 Financial and repayment features

- Credit and repayment history.
- Recent payment failures or reversals.
- Account tenure and transaction velocity.
- Loan amount, income, debt, and affordability consistency.
- Repeated use of the same bank account or payment instrument.
- Chargeback, dispute, and prior fraud outcomes.

### 4.5 Graph features

- Shared device count.
- Shared address, phone, email, bank account, or payment instrument count.
- Neighbor fraud rate.
- Connected-component size.
- Number of links to blocked or high-risk entities.

## 5. Labeling and Training Data

Fraud labels may arrive after the original decision, so labels must include an observation window and source.

Suggested labels:

- `CONFIRMED_FRAUD`
- `LEGITIMATE`
- `SUSPICIOUS_PENDING`
- `INCONCLUSIVE`

Do not treat an unreported transaction as automatically legitimate. Define a maturity window, such as 30 to 90 days depending on the lending journey, before using outcomes as negative examples.

Prevent leakage by ensuring every feature is calculated using only information available before the decision timestamp. Use time-based splits so future fraud patterns do not appear in training for earlier decisions.

## 6. Imbalanced Classification Metrics

Accuracy is not an appropriate primary metric when fraud is rare. Track:

- Precision: proportion of flagged cases that are truly fraudulent.
- Recall: proportion of fraud that is detected.
- F1 or F-beta: balance recall and precision according to business cost.
- PR-AUC: useful for rare positive classes.
- False-positive rate and legitimate approval rate.
- Expected financial loss and prevented loss.
- Review rate and step-up completion rate.
- Decision latency.

Choose thresholds using a cost matrix rather than a default probability such as 0.5. For example, missing a high-value fraud event should cost more than sending a legitimate customer to step-up verification.

## 7. Risk Score and Decision Policy

An illustrative combined score is:

```text
combined_risk =
    0.60 * supervised_risk
  + 0.20 * anomaly_risk
  + 0.20 * graph_risk
```

The weights must be learned and validated using historical outcomes; they are starting values only. Calibrate the final score and define policy thresholds by transaction type and customer segment.

Example policy:

| Risk range | Action | Typical rationale |
|---|---|---|
| 0.00 - 0.35 | Approve | Low risk and no hard rule hit |
| 0.35 - 0.65 | Step up | More verification can resolve uncertainty |
| 0.65 - 0.85 | Manual review | Material risk or conflicting evidence |
| 0.85 - 1.00 | Decline or block | High-confidence fraud or mandatory rule |

The ranges should be tuned against fraud loss, customer friction, operational capacity, and regulatory requirements.

## 8. Explainability

Return short, stable reason codes instead of exposing raw model internals. Examples include:

- `NEW_DEVICE`
- `HIGH_APPLICATION_VELOCITY`
- `SHARED_PAYMENT_INSTRUMENT`
- `IDENTITY_MISMATCH`
- `UNUSUAL_LOCATION`
- `KNOWN_RISKY_NETWORK`
- `BEHAVIOR_DEVIATION`

For analysts, store top positive and negative feature contributions, the feature values used, rule matches, model version, and score-calibration version. Explanations should be consistent with the actual decision and should not reveal controls in a way that helps fraudsters bypass them.

## 8A. Responsible AI and Transparency

- **Human oversight:** medium-confidence outcomes go to manual review rather than automatic denial.
- **Reason codes:** every challenged, reviewed, or declined transaction has understandable evidence.
- **Data minimization:** collect only signals needed for fraud prevention and retain them for a defined period.
- **Fairness review:** compare false-positive, false-negative, approval, and step-up rates across relevant customer segments.
- **No protected attributes by default:** do not use protected characteristics or unexplained proxy variables.
- **Auditability:** store model version, feature schema, policy version, score, reason codes, and decision timestamp.
- **Appeals and correction:** allow authorized staff to challenge an outcome and record the resolution.
- **Security against manipulation:** do not expose exact thresholds or sensitive feature values in customer-facing messages.

Customer-facing explanations should be useful but limited, such as: "Additional verification is required because this application differs from recent account activity." Analysts can receive more detailed feature contributions under role-based access.

## 9. Model Lifecycle and Monitoring

1. Ingest events and resolve entities.
2. Build point-in-time-correct training data.
3. Train, validate, calibrate, and document the model.
4. Compare against the current champion model.
5. Deploy first in shadow mode.
6. Run a controlled release with rollback support.
7. Monitor performance, drift, fairness, latency, and business impact.
8. Retrain on a schedule and when drift or fraud patterns justify it.

Monitor:

- Feature drift and missing values.
- Score distribution drift.
- Precision and recall after labels mature.
- Segment-level false positives and approval rates.
- Model and rules contribution rates.
- Data pipeline freshness and training-serving skew.
- Adversarial changes in devices, networks, and application behavior.

For the demo, show at least one evaluation artifact containing the dataset split, class distribution, precision, recall, PR-AUC, false-positive rate, threshold, and confusion matrix. A single accuracy number is not sufficient evidence for a fraud model.

## 10. Fairness and Governance

Do not use protected characteristics or proxy features without a documented legal and risk review. Evaluate false-positive and false-negative rates across relevant customer segments. Keep a model card containing intended use, limitations, training period, features, metrics, thresholds, known biases, approval owner, and rollback procedure.

## 11. Hackathon Demonstration Plan

For a compelling demo, show three scenarios:

1. A normal returning customer is approved with low latency.
2. A suspicious application triggers step-up verification because of a new device, high velocity, and identity mismatch.
3. Several accounts linked to one device or payment instrument form a risky cluster and are sent to manual review or blocked.

Display the decision, score, reason codes, model version, event timeline, and analyst feedback. This demonstrates both detection quality and the platform's ability to explain and learn from decisions.

## 12. Recommended Code and Test Boundaries

Keep model code independently testable:

- `feature_builder`: transforms validated events into point-in-time features.
- `rule_scorer`: evaluates deterministic rules and returns reason codes.
- `model_predictor`: loads a versioned artifact and returns raw model scores.
- `score_combiner`: combines supervised, anomaly, and graph scores.
- `decision_policy`: maps calibrated risk and hard rules to an action.
- `explainer`: maps technical contributions to safe reason codes.
- `model_monitor`: calculates drift and post-label performance metrics.

Minimum unit tests should cover missing features, boundary thresholds, duplicate events, unknown categories, model-load failure, and conflicting rule/model signals. Integration tests should verify that the API returns a stable schema and persists the model version and explanation with every decision.
