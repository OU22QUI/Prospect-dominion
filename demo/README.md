# Prospect Dominion Demo

This is a standalone front-end demo package for Prospect Dominion. It is intentionally separated from the full product stack so it can be shared with testers, prospects, or clients without exposing the internal implementation details.

## Use
Open `index.html` in a browser or serve the folder with any simple static server.

Example:

```bash
cd demo
python -m http.server 8000
```

Then open the local address shown in the terminal.

The available public path is `/tester.html`, which presents the product story without exposing backend implementation details.

## Purpose
This demo presents the product concept and its value proposition in a polished, customer-safe UI:
- signal flow,
- workflow health,
- account prioritization,
- warm-introduction visibility,
- governance and trust posture.

## Notes
This is a product showcase layer, not the actual backend implementation. It is designed to give prospects and testers a tangible preview of the operating model while keeping internal architecture and implementation details out of the public-facing experience.
