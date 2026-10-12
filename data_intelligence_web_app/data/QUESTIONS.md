n

# QUESTIONS.md
Management questions the Brighton Beryl bikeshare data should be able to answer.

Data available:
- DEMO_DATA.csv / station status+information snapshot — one row per station: bikes & docks
  available, capacity, is_installed / is_renting / is_returning, per-vehicle-type counts
  (scooter, e-BBE, manual bike), lat/lon.
- history.csv — repeated snapshots over time (station_id, live bikes & docks).
- free_bike_status.csv, geofencing zones, system pricing plans, vehicle_types.

These are questions to run against the data, not answers. No findings intended —
treat every bullet as a hypothesis to test with a chart or a number.

--------------------------------------------------------------

## 1. Is supply matched to demand, station by station?

- Which stations are chronically full (no free dock for most of the day) and which are
  chronically empty (no bike)? How many hours/day is each station in each state?
- Do high-capacity (large) stations show better utilisation or just more idle stock?
- For each station, what is the average / median fill level (% of capacity occupied) and
  how tightly does it cluster? Wide variance = unpredictable demand.
- Along the seafront vs the hilly northern stations: which cluster leans empty and which
  leans full, and does that match how their capacity was originally sized?
- How often does a station flip between "usable" and "starved"? Frequent flips point to
  demand spikes, not steady under-supply.

## 2. Are bikes and docks ever in the WRONG place at the WRONG time?

- Where are the empty stations during the morning commute, and are the same stations the
  full ones in the evening (the classic inbound/outbound imbalance Beryl must rebalamce)?
- Do the empties cluster geographically? Is there a supply desert — an area where a rider
  has several consecutive full/empty stations nearby with no walkable alternative?
- Which direction does net flow travel across the day (into the city vs out to Hove/the
  Marina), and by how many bikes/hour at peak?
- At the main rail hubs (Brighton Station North/South, Hove Station) — during peak
  arrivals do they run empty faster than the rebalance fleet can restock them?
- Are the "wrong place" problems the same on weekdays vs weekends (commuter flow vs leisure
  flow), and on dry vs wet days?

## 3. Fleet composition — are we stocking the right mix per location?

- Some stations stock only manual bikes, others only scooters; do stations offering a
  multi-type mix serve more trips or fewer "no bike" minutes than single-type stations?
- Scooters, e-BBE and manual bikes have different ranges and are suited to different terrain.
  Do the hilly/steep stations carry e-bikes and is e-supply correlated with how quickly stock
  runs dry? Which vehicle type is most likely to be "the last one left" at a depleted station?
- When a station empties, is it all types at once, or does one type linger unavailable?
- Which stations hold stock that is slow to move (idle for long) — locking capital in the
  wrong type for that neighbourhood?

## 4. Availability and service quality (the rider's experience)

- Which stations report is_renting / is_returning = False, how long, and do they coincide
  with the busiest locations (max impact of a station outage)?
- What is the real-world "assurance" at each station: given the last 24h of data, what
  fraction of the time would a rider find at least one bike and one free dock?
- Are outages clustered (whole area down) or random single stations?
- How fast does a station recover once flagged unavailable — is there a pattern of slow restock?

## 5. Network geometry and coverage

- Plot stations against the geofenced no-ride / no-parking zones: are any stations placed
  such that riders can't legally end a trip nearby, creating phantom "nearbys"?
- What is the walking distance between neighbouring stations? Are there gaps (two stations
  further apart than the network norm) that would be better served by a new or relocated dock?
- Is capacity distributed according to where people actually are, or inherited from where the
  original launch chose to build docks?

## 6. Operational efficiency and rebalancing

- How many bikes would need to be moved, and between which station pairs, to reach "no
  station empty and no station full" at the morning and evening peaks (a minimal rebalance
  plan)? How costly is that in vehicle movements?
- Which stations are the persistent donation or persistent collection points — the natural
  anchors a rebalancing route should start/end at?
- If total fleet bikes were redistributed by capacity rather than left in place, how many
  stations would change stock level — i.e. is the fleet parked proportionally to dock space?

## 7. Time patterns (from history.csv)

- What are the peak and trough hours for the whole network, and are the top-demand and
  bottom-demand hours at different times at different stations (network vs local peaks)?
- On a daily cycle, where does stock "pile up" overnight, and does morning rebalancing keep
  up before first commute?
- Which stations see smooth, predictable demand vs spiky, event-driven demand (Palace Pier,
  i360, cricket ground, Marina on match/holiday days)?
- Day-of-week and weekend vs weekday behaviour: which stations only matter on weekends?

## 8. Pricing and revenue (pricing plans + usage)

- If trips are correlated to station utilisation, which stations are the revenue engines and
  which are loss-leaders that only justify themselves as network coverage?
- Is there a utilisation threshold below which a station is effectively a write-off — and
  how many stations sit under it?

## 9. Data-quality questions to validate before trusting any of the above

- last_reported is a single timestamp per snapshot here — how fresh is it, and are some
  stations reporting stale data (a station that "looks full" but stopped reporting)?
- Are num_bikes + num_docks ever inconsistent with capacity (e.g. bikes+docks > capacity,
  or free_bike_status bikes not in any dock) — i.e. which rows are garbage and should be
  dropped before analysis?
- Is every station_id present in every snapshot, or do stations appear/disappear over time?
- Do counts reconcile across feeds (bikes in station_status vs free bikes vs capacity)?
