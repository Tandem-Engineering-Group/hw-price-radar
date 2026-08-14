# Bahamas Grid Portal

Single-file grid intelligence portal for the Commonwealth of The Bahamas.

Tabs:
- **Chart** — interactive schematic chart: 31 islands, 34 generation/LNG/planned-RE
  assets, pan + pinch-zoom, keyboard-accessible markers, full asset list.
- **Balance** — supply vs. peak demand for every grid.
- **Solar+BESS** — PV + storage screening calculator.
- **LNG** — Shell/FOCOL supply chain and risk register.
- **Ownership** — who controls what, domicile, stake, and openings for third
  parties to stabilise the grid. Confidence chips describe *this page's sourcing*.
- **Sim** — 24-hour dispatch simulation across day/night and wind/no-wind cycles,
  with peak-shaving storage dispatch to a solved thermal ceiling.
- **Fuel Log** — diesel vs LNG: $/MWh, arrival cadence, 120-day delivery timing,
  ISO-container distribution to the Family Islands, and the hurricane case.

- Zero dependencies, one `index.html`, served via GitHub Pages
- Data vintage: Aug 2026 (BPL, FOCOL/Shell EMP, Tribune242, EWN, LNG Prime, GEM, IDB)
- Family Island station capacities flagged EST pending URCA published data
- All simulation and cost output is **screening-level** — assumptions are listed
  in-page next to each model. 8760-hour dispatch modelling is required for design.
