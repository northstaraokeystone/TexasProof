# TexasProof v1.0 Specification

## Purpose

Monte Carlo simulation for Texas political fraud detection. Targets 2023-2025 fraud vectors with >95% detection rate.

## Input Sources

- **Texas Government Contracts**: Operation Lone Star emergency/no-bid contracts ($11B+ 2023-2025)
- **PAC Filings**: FEC and TEC filings (Dunn/Wilks $14M+, Texans United $3M+)
- **Property Records**: County deed records for Colony Ridge-style churning
- **University Audits**: TSU and other public university financial statements
- **Lottery Commission Data**: IGT and vendor political contributions
- **Blind Trust Filings**: AG office disbursement records

## Output Artifacts

- **Fraud Probability Scores**: 0-1 probability per record
- **Receipt Chains**: JSONL append-only ledger with dual-hash integrity
- **Dashboard Visualizations**: HTML dashboards per fraud vector
- **Simulation Results**: Monte Carlo run statistics

## Receipt Types

| Receipt Type | Purpose |
|--------------|---------|
| `ingest_receipt` | Record ingested for analysis |
| `ols_contractor_receipt` | OLS contractor fraud detection result |
| `pac_influence_receipt` | PAC influence pipeline detection result |
| `predatory_lending_receipt` | Colony Ridge-style churn detection |
| `unauthorized_invoice_receipt` | TSU-type unauthorized invoice detection |
| `trust_disbursement_receipt` | Blind trust anomaly detection |
| `prohibited_contribution_receipt` | IGT-style prohibited contribution |
| `wound_receipt` | System wound requiring attention |
| `genesis_birth_receipt` | Watcher agent spawned |
| `sim_complete_receipt` | Simulation run completed |
| `anomaly_receipt` | Anomaly detected in system |

## SLOs (Service Level Objectives)

| Metric | Threshold | Action on Breach |
|--------|-----------|------------------|
| Detection Rate (Baseline) | ≥95% | Halt simulation |
| Resilience (α) | ≥0.70 | Escalate |
| Latency per Record | ≤500ms | Alert |
| Memory Usage | ≤8GB | Compaction |
| Self-Spawn Latency | ≤500 cycles | Review thresholds |

## Stoprules

1. **Detection Rate < 70%**: Halt simulation, trigger architecture review
2. **Memory > 8GB**: Trigger compaction, halt if compaction fails
3. **Consecutive Gate Failures > 2**: Stop project, require human review
4. **α < 0.50**: System under attack, escalate to human oversight

## Rollback Protocol

1. On validation failure, revert to last anchored state
2. Emit `rollback_receipt` with reason and target state
3. Re-run validation from anchored state
4. If rollback fails, halt system and page human

## 6 Mandatory Scenarios

1. **BASELINE**: OLS contractor detection ≥95%
2. **STRESS**: PAC detection under 50% political pressure, α ≥0.70
3. **GENESIS**: Self-spawn watchers from wound patterns
4. **COLONY_RIDGE**: Predatory lending churn detection ≥90%
5. **FUND_DIVERSION**: TDCJ→OLS budget shift detection ≥85%
6. **GÖDEL**: Edge cases with graceful failure

## Fraud Vectors (from Grok Research)

### Operation Lone Star ($11B+)
- Emergency/no-bid contracts to politically connected contractors
- Gothams: $65M emergency contract
- Wynne Transportation: $220M at $1,800/passenger
- TDCJ diversion: $359.6M shifted from prisons

### PAC Influence Pipeline ($14M+)
- Tim Dunn: $9.7M to Defend Texas Liberty
- Farris Wilks: $4.8M to Defend Texas Liberty
- Texans United: $3M targeting Paxton impeachment voters

### Colony Ridge Predatory Lending
- 30% foreclosure rate (15x national average)
- Properties churned 2-4+ times in 3 years
- Seller-financed loans to vulnerable populations

### TSU Probe
- Hundreds of millions in unauthorized invoices
- FY2023 audit: 10 months late
- FY2024 audit: 4 months late
- Probe ordered by Abbott, November 2025

### IGT Lottery
- $180,000 fine for prohibited contributions to caucuses

### Paxton Blind Trust
- $20,000 disbursement to Ken and Angela Paxton for legal fees
- Records unsealed December 19, 2025

---

**Version**: 1.0.0
**Last Updated**: 2025-12-26
**Status**: ACTIVE
