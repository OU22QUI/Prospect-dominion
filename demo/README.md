# Prospect Dominion Demo

This is the public Prospect Dominion product experience: a customer-facing homepage, product simulation, pilot pricing, partner model, and technical evaluation path.

## Use
Open `index.html` in a browser or serve the folder with any simple static server.

Example:

```bash
cd demo
python -m http.server 8000
```

Then open the local address shown in the terminal.

Public paths:

- `/` — product homepage and walkthrough request
- `/demo/` — simulation with sample accounts
- `/pricing/` — pilot and deployment pricing
- `/partners/` — partner model
- `/tester.html` — technical evaluation instructions

## Optional configuration

`config.js` accepts public, non-secret endpoints for a lead form and analytics sink:

```js
window.PD_DEMO_CONFIG = {
	requestEndpoint: "https://example.com/demo-request",
	analyticsEndpoint: "https://example.com/demo-events"
};
```

Leave both values empty for a credential-free public demo. Requests and events remain local to the browser session when no endpoint is configured.

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
