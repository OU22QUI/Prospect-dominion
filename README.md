# Prospect Dominion

### A governed revenue operating layer for teams that need to know where to move next.

Prospect Dominion turns scattered buying signals into a ranked account queue, a credible relationship path, and a controlled next action.

**[Open the live demo](https://ou22qui.github.io/Prospect-dominion/)** · **[Explore the product path](https://ou22qui.github.io/Prospect-dominion/tester.html)**

## What you can see

- **Signal intelligence**: identify which accounts deserve attention now.
- **Account prioritization**: compare intent, stage, score, and buying context.
- **Relationship paths**: see the people and routes that can make an introduction credible.
- **Governed execution**: run a signal scan, queue a warm introduction, or approve outreach.
- **Operational trust**: keep human review in the loop as work moves from signal to action.

## Try it

Open the [live demo](https://ou22qui.github.io/Prospect-dominion/) and scroll to **Account command center**.

1. Select an account from the queue.
2. Switch between expansion, renewal, new-logo, and cross-sell scenarios.
3. Review the signal, relationship path, and activity stream.
4. Run a recommended action and watch the account state update.

The demo is a standalone public experience. It uses a curated dataset so it can be opened without credentials or setup.

## Run locally

```bash
cd demo
python -m http.server 8000
```

Then open `http://127.0.0.1:8000`.

## Public boundary

This repository publishes the customer-facing demo only. Internal product notes, commercial planning, deployment material, and implementation documentation remain outside the public repository.

The public demo is intentionally separate from the full product stack. It demonstrates the operating model and interaction quality without requiring access to private services or customer data.

## License

This repository is a private product demonstration for Prospect Dominion. It is not licensed for reuse, redistribution, or production deployment.
