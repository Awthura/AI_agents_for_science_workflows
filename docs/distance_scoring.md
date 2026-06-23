# Distance Scoring

This document explains how the distance score is computed for each conference recommendation.

---

## Why Distance?

Attending a conference involves travel. A researcher in Germany faces very different travel costs attending a conference in Athens vs. one in Tokyo. Distance is therefore one of the three scoring axes, weighted at **30%** of the total score.

The guiding principle: **closer is better**, but distance is not a hard cutoff — a far-away A* conference should still be recommendable, just ranked lower than a nearby equivalent.

---

## Step 1 — Address to Coordinates (Geocoding)

Both the researcher's address and the conference location are converted to geographic coordinates `(latitude, longitude)` using [Nominatim](https://nominatim.org/) — the geocoding API of OpenStreetMap.

```python
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="conference-recommender/1.0")
location = geolocator.geocode("Otto-von-Guericke-Universität, Magdeburg, Germany")
# → Coordinates(lat=52.139, lon=11.646)
```

If geocoding fails (location string is ambiguous, service unavailable, etc.), the distance score defaults to **50.0** — a neutral mid-range value that neither rewards nor penalises the conference.

---

## Step 2 — Haversine Distance

Once both points have coordinates, the straight-line distance on the Earth's surface is computed using the **Haversine formula**. This gives the great-circle distance — the shortest path between two points on a sphere.

$$
a = \sin^2\!\left(\frac{\phi_2 - \phi_1}{2}\right) + \cos\phi_1 \cdot \cos\phi_2 \cdot \sin^2\!\left(\frac{\lambda_2 - \lambda_1}{2}\right)
$$

$$
d = 2R \cdot \arcsin\!\left(\sqrt{a}\right), \qquad R = 6371 \text{ km}
$$

This is more accurate than a flat-plane distance, especially over long distances.

**Example — Magdeburg to Athens:**
```
Magdeburg:  52.139°N, 11.646°E
Athens:     37.984°N, 23.728°E

Haversine → 1,906 km
```

---

## Step 3 — Kilometres to Score (Exponential Decay)

A raw distance in km is not directly useful as a score. We need a function that:
- Returns **100** at 0 km (same city)
- Returns **~50** at a moderate distance (~5,000 km)
- Approaches **0** at very long distances (~15,000 km)
- Never returns exactly 0 (even Antarctica is still reachable)

We use **exponential decay**:

$$
s_{\text{dist}}(d) = 100 \cdot \exp\!\left(-\frac{3d}{d_{\max}}\right), \qquad d_{\max} = 15{,}000 \text{ km}
$$

```python
def distance_to_score(km: float, max_km: float = 15_000.0) -> float:
    return round(100.0 * math.exp(-3.0 * km / max_km), 1)
```

### Score table

| Distance | Example route | Score |
|---|---|---|
| 0 km | Same city | 100.0 |
| 200 km | Magdeburg → Berlin | 96.1 |
| 500 km | Magdeburg → Amsterdam | 90.5 |
| 1,000 km | Magdeburg → Paris | 81.9 |
| 1,906 km | Magdeburg → Athens | 68.3 |
| 3,000 km | Magdeburg → Dubai | 54.9 |
| 5,000 km | Magdeburg → New York | 36.8 |
| 8,000 km | Magdeburg → Tokyo | 20.0 |
| 10,000 km | Magdeburg → Singapore | 13.5 |
| 15,000 km | Magdeburg → Antipode | 5.0 |

### Decay curve

```
Score
100 |·
    | ·
 80 |   ·
    |     ·
 60 |       ·
    |          ·
 40 |               ·
    |                    ·
 20 |                          ·
    |                                ·
  0 +─────────────────────────────────── km
    0    3000   6000   9000  12000  15000
```

---

## Real Examples from the Pipeline

**Researcher at Otto-von-Guericke-Universität, Magdeburg, Germany:**

| Conference | Location | Distance | Score |
|---|---|---|---|
| ICAIF | Milan, Italy | ~861 km | 86 |
| ISC | Rennes, France | ~1,350 km | 77 |
| EACL | Athens, Greece | ~1,906 km | 69 |
| AAAI | Montréal, Canada | ~6,500 km | 31 |
| ICTAI | Boca Raton, USA | ~7,800 km | 21 |
| PRICAI | Guangzhou, China | ~8,600 km | 17 |
| ACCV | Osaka, Japan | ~9,200 km | 17 |

**Researcher at ETH Zurich, Switzerland:**

| Conference | Location | Distance | Score |
|---|---|---|---|
| ISC | Rennes, France | ~1,100 km | 86 |
| AAAI | Montréal, Canada | ~6,200 km | 30 |
| USENIX SECURITY | Denver, USA | ~8,600 km | 19 |
| ASIACCS | Macau, China | ~9,500 km | 16 |

---

## Why Exponential Decay (and not linear)?

A linear scale would unfairly penalise any overseas conference. With exponential decay:
- The difference between 0 km and 500 km (local vs. national) is meaningful (~10 points)
- The difference between 8,000 km and 10,000 km (two long-haul flights) is small (~7 points)
- A conference in Tokyo and one in Singapore are nearly equivalent from a European perspective

This matches how researchers actually think: the first 1,000 km matter a lot; beyond ~5,000 km, it's all "long-haul" and the score difference is minor.

---

## Fallback (Geocoding Failure)

If either the researcher's address or the conference city cannot be geocoded, the distance score is set to **50.0**. This appears in the output as a flat `Dist: 50` for multiple conferences — it means the location string was ambiguous or the geocoder timed out, not that every conference is equidistant.

Common causes:
- Conference city strings like `"Disney Springs, Buena Vista, FL, USA"` are too specific for Nominatim
- Chinese city + province strings sometimes fail to resolve
- Nominatim rate-limiting (max 1 request/second) — if too many requests fire in quick succession, later ones time out

The geocoding implementation includes:
- A **1.1s rate limiter** between requests to respect Nominatim's policy
- An **LRU cache** so each unique address is only queried once per process
- **Pre-geocoding of the user's address** once per profile run (not once per conference)

---

## Integration in the Total Score

$$
s_{\text{total}} = 0.50 \cdot s_{\text{rel}} + 0.30 \cdot s_{\text{dist}} + 0.20 \cdot s_{\text{pres}}
$$

Distance contributes **30%**. A conference 10,000 km away (score ~13) vs. one 500 km away (score ~90) creates a difference of ~23 points in the distance component, or ~7 points in the total score. Relevancy and prestige dominate — distance is a tiebreaker and travel-cost proxy, not a decisive filter.
