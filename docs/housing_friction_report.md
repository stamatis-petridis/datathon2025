# Housing Friction Atlas: Mapping Greece's Locked Stock Crisis

A compact overview of Greece’s housing friction patterns using ELSTAT 2021 dwelling data.  

## Friction Model

### Starting Point: Basic Price Equation

In a frictionless market, price is determined by demand over supply:

$$P = P_0 \left(\frac{D}{S}\right)^\alpha$$

For simplicity, assume $P_0 = 1$ and $\alpha = 1$:

$$P = \frac{D}{S}$$

This says: more demand raises prices, more supply lowers them.

### The Problem: Not All Supply is Available

Greece has 6.6 million dwellings. But 2.3 million are locked — vacant, vacation homes, secondary residences, stuck in probate, or otherwise unavailable.

The market doesn't operate on total supply $S_{total}$. It operates on effective supply:

$$S_{eff} = S_{total} - S_{locked}$$

So the real price equation is:

$$P = \frac{D}{S_{eff}}$$

### Defining Friction

Let $\sigma$ be the share of locked stock:

$$\sigma = \frac{S_{locked}}{S_{total}}$$

Then:

$$S_{eff} = S_{total}(1 - \sigma)$$

Substituting into the price equation:

$$P = \frac{D}{S_{total}(1 - \sigma)} = \frac{D}{S_{total}} \cdot \frac{1}{1-\sigma}$$

### The Friction Factor

Define:

$$F = \frac{1}{1-\sigma}$$

Now the price equation becomes:

$$P = \frac{D}{S_{total}} \cdot F$$

**$F$ is the friction multiplier.** It tells you how much locked stock inflates prices beyond what total supply would suggest.

### Intuition Table

| $\sigma$ (locked share) | $F$ (friction) | Effect on Price |
|-------------------------|----------------|-----------------|
| 0% | 1.00 | No friction |
| 25% | 1.33 | Prices 33% higher |
| 34.5% (Greece avg) | 1.53 | Prices 53% higher |
| 50% | 2.00 | Prices doubled |
| 80% | 5.00 | Prices 5× higher |

### Greece's Reality

National average: $\sigma = 0.345$, so $F = 1.53$

The market behaves as if demand is 53% higher than reality — not because people want more housing, but because 2.3 million homes are invisible to the market.

### Decomposing Friction: What Locks the Stock?

<div align="center">![](../outputs/national_locked_stock_pie.png){ width=70% }</div>

Total friction is the product of independent friction sources:

$$F = \prod_i F_i = F_1 \cdot F_2 \cdot F_3 \cdot F_4$$

Each $F_i$ corresponds to a category of locked stock:

$$F_i = \frac{1}{1 - \sigma_i}$$

Where $\sigma_i$ is each category's share of **total** dwellings.

### Friction Components (Greece 2021)

| Component | Category | Units | $\sigma_i$ | $F_i$ |
|-----------|----------|-------|------------|-------|
| $F_1$ | Vacation / secondary homes | 1,483,734 | 22.5% | 1.290 |
| $F_2$ | Empty for rent | 406,885 | 6.2% | 1.066 |
| $F_3$ | Other empty / locked | 327,496 | 5.0% | 1.053 |
| $F_4$ | Empty for sale | 59,471 | 0.9% | 1.009 |

### Verification

$$F = F_1 \cdot F_2 \cdot F_3 \cdot F_4 = 1.290 \times 1.066 \times 1.053 \times 1.009 \approx 1.46$$

Note: The multiplicative model slightly underestimates total $F = 1.53$ because the $\sigma_i$ values overlap in the additive model. For policy purposes, the additive decomposition ($\sigma = \sum \sigma_i$) is cleaner, but the multiplicative form shows how **each friction source compounds**.

### Policy Insight

| Friction Source | $F_i$ | Policy Lever |
|-----------------|-------|--------------|
| $F_1$ (Tourism) | 1.290 | STR caps, vacancy tax, seasonal conversion |
| $F_2$ (Rent market) | 1.066 | Faster matching, rent guarantees, tenant protections |
| $F_3$ (System failure) | 1.053 | Inheritance reform, cadastre cleanup, rehab grants |
| $F_4$ (Sale market) | 1.009 | Transaction cost reduction, faster notary process |

**Tourism alone accounts for 29% price inflation.** The other sources add ~15% combined. This confirms: Greece's housing crisis is primarily a tourism extraction problem.
**National data snapshot (Greece, National census 2021)**  
- Total dwellings ($S_{\text{total}}$): 6,596,782 (normal dwellings)
- Empty for rent: 406,885 
- Empty for sale: 59,471
- Vacation/secondary homes: 1,483,734 (856,991 vacation + 626,743 secondary)
- Other empty/locked: 327,496
- Locked stock ($\sigma \cdot S_{\text{total}}$): $\approx 2{,}277{,}608$ dwellings

## Executive snapshot

- $\sigma$ measures the share of homes that exist but are not accessible (not rented, not sold, not used). 
- $F$ describes how much tighter the market behaves because this stock is locked.
- National values: $\sigma \approx 0.345$ and $F \approx 1.53$.
Archetypes across 333 municipalities (EU benchmark buckets):

- EU Efficient: 1 
- EU Normal: 17 
- Mediterranean Acceptable: 34 
- Elevated Friction: 37 
- Structural Dysfunction: 109 
- Market Collapse: 135 

Includes: friction map, archetype map, and top-$\sigma$ composition charts.

## Method
- Inputs: ELSTAT 2021 dwelling status by municipality; computed σ per municipality; shares by rent/sale, tourism (vacation+secondary), other reasons.
- Friction: $F = \frac{1}{1-\sigma}$.
- Archetypes (EU-style benchmark):
  - EU Efficient: σ < 0.10
  - EU Normal: 0.10 ≤ σ < 0.15
  - Mediterranean Acceptable: 0.15 ≤ σ < 0.20
  - Elevated Friction: 0.20 ≤ σ < 0.30
  - Structural Dysfunction: 0.30 ≤ σ < 0.50
  - Market Collapse: σ ≥ 0.50


## Maps
- Friction (σ) map:
  <div align="center">![](../outputs/choropleth_municipalities.png){ width=100% }</div>
- Archetype map:
  <div align="center">![](../outputs/choropleth_archetypes.png){ width=100% }</div>

## EU Benchmark Classification

### At a Glance

| Category | σ Range | Count | Avg σ | Status | Color |
|----------|---------|-------|-------|--------|-------|
| EU Efficient | < 10% | 1 | 9.0% | Northern European standard | Dark green |
| EU Normal | 10–15% | 17 | 13.2% | Central European standard | Green |
| Mediterranean Acceptable | 15–20% | 34 | 17.5% | Southern European standard | Light green |
| Elevated Friction | 20–30% | 37 | 25.7% | Above EU norms | Yellow |
| Structural Dysfunction | 30–50% | 109 | 41.0% | No EU equivalent | Orange |
| Market Collapse | ≥ 50% | 135 | 59.7% | No EU equivalent | Red |

**Total: 333 municipalities**

---

### What Drives Each Category?

| Category | Tourism | Market (Rent/Sale) | System Failure | Primary Driver |
|----------|---------|-------------------|----------------|----------------|
| EU Efficient | 3.7% | 2.7% | 2.6% | — (balanced) |
| EU Normal | 4.8% | 4.0% | 4.3% | — (balanced) |
| Mediterranean Acceptable | 6.6% | 5.8% | 5.2% | — (balanced) |
| Elevated Friction | 13.6% | 6.2% | 6.0% | Tourism emerging |
| Structural Dysfunction | 29.8% | 5.6% | 5.6% | **Tourism dominant** |
| Market Collapse | 49.5% | 6.3% | 3.9% | **Tourism extreme** |

**Key insight:** Market friction (~6%) and system failure (~5%) are constant across all categories. Tourism is the variable that separates functional markets from collapsed ones.

---

### Policy Response Matrix

| Category | Urgency | Focus | Instruments |
|----------|---------|-------|-------------|
| EU Efficient | None | Preserve | Monitor only |
| EU Normal | Low | Maintain | Light monitoring, preserve affordability |
| Mediterranean Acceptable | Watch | Prevent drift | Early warning, gentle STR guardrails |
| Elevated Friction | Moderate | Active intervention | STR limits, LTR incentives, targeted rehab |
| Structural Dysfunction | High | Strong intervention | Vacancy taxes, rehab grants, enforcement |
| Market Collapse | Critical | Emergency measures | STR caps, vacancy tax, inheritance reform, social housing |

---

### The Bottom Line

- **52 municipalities (16%)** meet European standards (σ < 20%)
- **244 municipalities (73%)** are in dysfunction or collapse (σ > 30%)
- **Only Vrilisia** (σ = 9%) operates at Northern European efficiency
- **Tourism extraction** is the sole differentiator between healthy and broken markets


## Focus: major cities
- Compare archetype and σ for Αθήνα, Θεσσαλονίκη, Πειραιάς, Πάτρα, Ηράκλειο, Λάρισα.
- Composition chart:
  <div align="center">![](../outputs/major_cities_composition.png){ width=100% }</div>

## Top-20 friction profiles
- Stacked composition:
  <div align="center">![](../outputs/top20_sigma_composition.png){ width=100% }</div>
- Narrative: most top-σ municipalities are tourism-heavy islands/coast; a few interior “locked” cases.

## Risks and caveats
- Name matching uses overrides between ELSTAT and GADM boundaries; minor mismatches possible.
- σ measures empty dwellings; not all are recoverable; “other_reason” may mix heterogeneous causes.
- Data year: 2021; post-2021 tourism shocks or housing policies not reflected.

## Next steps
- Add time-series (2011 vs 2021) to track friction trends.
- Merge price/rent data to link σ with affordability.
- Scenario: apply STR caps in Tourist Drain areas; model σ reduction and F improvement.

---

## Appendix - Unlock Simulation (20%)
A simulated 20% unlock of locked stock shows how prices respond when friction eases. We recompute σ, F, and price changes using the stylised price model; high-friction areas see the largest drops. Charts below show simulated σ, price change, and top-10 price drops.

<div align="center">![](../outputs/unlock_effect_collage.png){ width=100% }</div>

A 20% unlock shifts 88 municipalities from Market Collapse to lower tiers.
