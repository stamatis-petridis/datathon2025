# Housing Friction Atlas: Mapping Greece's Locked Stock Crisis

A compact overview of Greece’s housing friction patterns using ELSTAT 2021 dwelling data.  
Locked stock share: $\sigma = \frac{S_{\text{locked}}}{S_{\text{total}}}$.  
Friction factor: $F = \frac{1}{1 - \sigma}$.

## 2. Executive snapshot

- $\sigma$ measures the share of homes that exist but are not accessible (not rented, not sold, not used).  
- $F$ describes how much tighter the market behaves because this stock is locked.  
- National values: $\sigma \approx 0.345$ and $F \approx 1.53$.

Archetypes across 333 municipalities:

- Tourist Drain: 133  
- Transitional: 132  
- Healthy: 66  
- System Failure: 2  

Includes: friction map, archetype map, and top-$\sigma$ composition charts.

## 2. Method
- Inputs: ELSTAT 2021 dwelling status by municipality; computed σ per municipality; shares by rent/sale, tourism (vacation+secondary), other reasons.
- Friction: $F = \frac{1}{1-\sigma}$.
- Archetypes:
  - Tourist Drain: σ > 0.5 and tourism share > 0.3
  - System Failure: σ > 0.5 and tourism share ≤ 0.3
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

## 4. Archetype summary (from outputs/archetype_summary.json)
- Tourist Drain: 133; avg σ 0.597; avg tourism share 0.499; avg market 0.061; avg system-failure 0.036
- Transitional: 132; avg σ 0.387; avg tourism share 0.273; avg market 0.057; avg system-failure 0.058
- Healthy: 66; avg σ 0.173; avg tourism share 0.070; avg market 0.054; avg system-failure 0.050
- System Failure: 2; avg σ 0.583; avg tourism share 0.186; avg market 0.151; avg system-failure 0.246
- Total municipalities: 333

## 5. Composition insights
- Top-σ cases skew to tourism extraction (vacation/secondary) with small market churn.
- Healthy group: modest tourism share; balanced market turnover; lower “other” locked reasons.
- System Failure: tiny set with high “other”/market frictions, not tourism-driven.
- Transitional: mixed signals; watchlist for policy nudges.

## 6. Policy archetypes (decision table)
| Archetype | Trigger (σ / composition) | Policy focus | Instruments |
|-----------|---------------------------|--------------|-------------|
| Tourist Drain | σ > 0.5 & tourism > 0.3 | Cool tourism extraction, rebalance supply | STR caps/permits, tourist tax, incentives to shift to LTR, build-to-rent, seasonal conversion rules |
| System Failure | σ > 0.5 & tourism ≤ 0.3 | Unlock stuck stock, fix market failures | Rehab grants, tax penalties on chronic vacancy, probate/ownership cleanup, social housing acquisition |
| Transitional | 0.25–0.5 σ | Prevent drift upward | Light-touch STR regulation, monitoring, targeted rehab, modest incentives to LTR |
| Healthy | σ < 0.25 | Maintain balance | Monitoring, preserve affordability, gentle guardrails on STR |

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
