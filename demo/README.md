# Prospect Dominion Demo

This is the public Prospect Dominion product experience: a customer-facing homepage, product simulation, proposed pilot scope, deferred partner information, and technical evaluation path.

## Use
Open `index.html` in a browser or serve the folder with any simple static server.

Example:

```bash
cd demo
python -m http.server 8000
```

Then open the local address shown in the terminal.

Public paths:

- `/` — product overview and simulation
- `/demo/` — simulation with sample accounts
- `/pricing/` — proposed pilot scope and exclusions
- `/partners/` — partner program status (not open)
- `/tester.html` — technical evaluation instructions

## Optional configuration

`config.js` accepts an optional public, non-secret analytics endpoint:

```js
window.PD_DEMO_CONFIG = {
	analyticsEndpoint: "https://example.com/demo-events"
};
```

Leave the endpoint empty for a credential-free public demo. Demo interaction events are kept in `sessionStorage` for the current tab. The site does not collect or submit contact details; scheduling links open Cal.com in a separate tab.

## Purpose
The public experience presents the product concept and commercial path:
- signal flow,
- workflow health,
- account prioritization,
- warm-introduction visibility,
- governance and trust posture,
- one-workflow pilot scope,
- deployment and handover model.

## Notes
The account experience is a simulation using sample accounts and illustrative values. It does not connect to live customer data or send external actions. The technical evaluation path points to the real local deployment baseline.
