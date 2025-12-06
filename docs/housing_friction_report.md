# Housing Friction Atlas: Mapping Greece's Locked Stock Crisis

A compact overview of Greece’s housing friction patterns using ELSTAT 2021 dwelling data.  
Locked stock share: $\sigma = \frac{S_{\text{locked}}}{S_{\text{total}}}$.  
Friction factor: $F = \frac{1}{1 - \sigma}$.

**National data snapshot (Greece, National census 2021)**  
- Total dwellings ($S_{\text{total}}$): 6,596,782 (normal dwellings)  
- Empty for rent: 406,885  
- Empty for sale: 59,471  
- Vacation/secondary homes: 1,483,734 (856,991 vacation + 626,743 secondary)  
- Other empty/locked: 327,496  
- Locked stock ($\sigma \cdot S_{\text{total}}$): $\approx 2{,}277{,}608$ dwellings  

## 2. Executive snapshot

- $\sigma$ measures the share of homes that exist but are not accessible (not rented, not sold, not used).  
- $F$ describes how much tighter the market behaves because this stock is locked.  
- National values: $\sigma \approx 0.345$ and $F \approx 1.53$.

Archetypes across 333 municipalities:

- Problematic (tourism-driven or systemic): 135  
- Transitional: 132  
- Healthy: 66  

Includes: friction map, archetype map, and top-$\sigma$ composition charts.

## 2. Method
- Inputs: ELSTAT 2021 dwelling status by municipality; computed σ per municipality; shares by rent/sale, tourism (vacation+secondary), other reasons.
- Friction: $F = \frac{1}{1-\sigma}$.
- Archetypes (analysis groups):
  - Problematic: σ > 0.5 (includes both tourism-driven and system-failure cases)
  - Transitional: 0.25 ≤ σ ≤ 0.5
  - Healthy: σ < 0.25

### Price Model

$$P = P_0 \left(\frac{D \cdot F}{S}\right)^\alpha$$

Where:
- $P$ = market price (rent/purchase)
- $P_0$ = baseline price (construction cost floor)
- $D$ = demand
- $S$ = physical supply
- $F = \frac{1}{1-\sigma}$ = friction multiplier
- $\alpha$ = price elasticity (typically 1.2–1.8 for constrained markets)

**Interpretation:** Friction $F$ acts as a demand multiplier. When $\sigma = 0.345$, $F = 1.53$ — the market behaves as if demand is 53% higher than reality.

## 3. Maps (placeholders)
- Friction (σ) map:
  <div align="center">![](../outputs/choropleth_municipalities.png){ width=100% }</div>
- Archetype map:
  <div align="center">![](../outputs/choropleth_archetypes.png){ width=100% }</div>

## 4. Archetype summary (from outputs/archetype_summary.json, grouped)
- Problematic (Tourist Drain + System Failure): 135; avg σ 0.597; avg tourism share 0.495; avg market 0.063; avg system-failure 0.039
- Transitional: 132; avg σ 0.387; avg tourism share 0.273; avg market 0.057; avg system-failure 0.058
- Healthy: 66; avg σ 0.173; avg tourism share 0.070; avg market 0.054; avg system-failure 0.050
- Total municipalities: 333

## 5. Composition insights
- Top-σ cases skew to tourism extraction (vacation/secondary) with small market churn.
- Healthy group: modest tourism share; balanced market turnover; lower “other” locked reasons.
- Within the Problematic group, a small subset is driven more by “other”/market frictions than tourism.
- Transitional: mixed signals; watchlist for policy nudges.

## 6. Policy archetypes (decision table)
| Archetype   | Trigger (σ / composition)          | Policy focus                                      | Instruments |
|-------------|------------------------------------|---------------------------------------------------|-------------|
| Problematic | σ > 0.5 (tourism or system-failure)| Cool tourism extraction and unlock stuck stock    | STR caps/permits, tourist tax, rehab grants, tax penalties on chronic vacancy, probate/ownership cleanup, social housing acquisition |
| Transitional| 0.25–0.5 σ                         | Prevent drift upward                              | Light-touch STR regulation, monitoring, targeted rehab, modest incentives to LTR |
| Healthy     | σ < 0.25                           | Maintain balance                                  | Monitoring, preserve affordability, gentle guardrails on STR |

## 7. Focus: major cities (placeholders)
- Compare archetype and σ for Αθήνα, Θεσσαλονίκη, Πειραιάς, Πάτρα, Ηράκλειο, Λάρισα.
- Composition chart:
  <div align="center">![](../outputs/major_cities_composition.png){ width=100% }</div>

## 8. Top-20 friction profiles
- Stacked composition:
  <div align="center">![](../outputs/top20_sigma_composition.png){ width=100% }</div>
- Narrative: most top-σ municipalities are tourism-heavy islands/coast; a few interior “locked” cases.

## 9. Risks and caveats
- Name matching uses overrides between ELSTAT and GADM boundaries; minor mismatches possible.
- σ measures empty dwellings; not all are recoverable; “other_reason” may mix heterogeneous causes.
- Data year: 2021; post-2021 tourism shocks or housing policies not reflected.

## 10. Next steps
- Add time-series (2011 vs 2021) to track friction trends.
- Merge price/rent data to link σ with affordability.
- Scenario: apply STR caps in Tourist Drain areas; model σ reduction and F improvement.

---

## Appendix - Unlock Simulation (20%)
A simulated 20% unlock of locked stock shows how prices respond when friction eases. We recompute σ, F, and price changes using the stylised price model; high-friction areas see the largest drops. Charts below show simulated σ, price change, and top-10 price drops.

<div align="center">![](../outputs/unlock_effect_collage.png){ width=100% }</div>
