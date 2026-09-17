# Prospect Dominion Demo

This is a standalone front-end demo package for Prospect Dominion. It is intentionally separated from the full product stack so it can be shared with prospects or clients without exposing internal implementation details.

## Use
Open `index.html` in a browser or serve the folder with any simple static server.

Example:

```bash
cd demo
python -m http.server 8000
```

Then open the local address shown in the terminal.

The available public path is `/tester.html`, which presents the product story without exposing backend implementation details.

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
This demo presents the product concept and its value proposition in a polished, customer-safe UI:
- signal flow,
- workflow health,
- account prioritization,
- warm-introduction visibility,
- governance and trust posture.

## Notes
This is a product showcase layer, not the actual backend implementation. It is designed to give prospects and testers a tangible preview of the operating model while keeping internal architecture and implementation details out of the public-facing experience.
