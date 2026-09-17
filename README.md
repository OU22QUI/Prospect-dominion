# Prospect Dominion

### Know where to move next.

Prospect Dominion helps revenue teams turn scattered buying signals into a ranked account queue, a credible relationship path, and a controlled next action.

**[Open the live demo](https://ou22qui.github.io/Prospect-dominion/)** · **[Explore the product path](https://ou22qui.github.io/Prospect-dominion/tester.html)**

## Start here

Open the [live demo](https://ou22qui.github.io/Prospect-dominion/) and select **Account command center**.

The demo opens without an account, credentials, or installation. It uses a curated sample workspace so you can explore the product experience immediately.

## How to use the demo

1. Choose an account from the queue, or use the scenario buttons for Expansion, Renewal, New logo, and Cross-sell.
2. Read the account summary: intent, stage, buying signal, decision path, and score explanation.
3. Review the relationship map to see the people and paths connected to the opportunity.
4. Use **Run signal scan**, **Queue warm intro**, or **Approve outreach** to test a governed workflow action.
5. Use **Undo** to reverse the last action, or **Reset** to return the demo to its starting state.
6. Use search and filters to find accounts by company, intent, or stage.
7. Select **Compare** on another account to compare its score and priority with the selected account.
8. Use **Share** to copy a link that opens the current scenario.

Your changes are stored in your browser for the current demo workspace. No customer data is required.

## What Prospect Dominion shows

- **Signal intelligence**: identify which accounts deserve attention now.
- **Account prioritization**: compare intent, stage, score, and buying context.
- **Relationship intelligence**: see the people and routes that can make an introduction credible.
- **Governed execution**: make the next action visible before it is approved.
- **Operational trust**: keep human review in the loop for sensitive actions.

## Walkthrough request

Select **Book a live product walkthrough** in the demo to open the request form. Add your name, work email, role, company, and primary use case.

The public demo confirms the request locally. To connect the form to your own follow-up service, configure `demo/config.js` with a public HTTPS endpoint:

```js
window.PD_DEMO_CONFIG = {
	requestEndpoint: "https://example.com/demo-request",
	analyticsEndpoint: "https://example.com/demo-events"
};
```

Leave these values empty when running the demo without external services.

## Run the demo locally

```bash
cd demo
python -m http.server 8000
```

Open <http://127.0.0.1:8000> in your browser.

For the product path, open <http://127.0.0.1:8000/tester.html>.

## Local development

The public experience is plain HTML, CSS, and JavaScript, so no build step is required. After editing a file, refresh the browser page served from the `demo` directory.

Useful checks from the repository root:

```bash
node --check demo/script.js
python scripts/audit_public_demo.py
python scripts/validate_customer_config.py --env-file deploy/customer.env.example --check-public-demo
python -m pytest -q
```

## Deployment options

- **Demo**: share the hosted GitHub Pages experience.
- **Pilot**: use the interactive path to align a focused workflow with a revenue team.
- **Private deployment**: connect the operating model to a controlled customer environment.

## Support

For a guided walkthrough or pilot conversation, use the request form in the live demo.

## License

This repository is a private product demonstration for Prospect Dominion. It is not licensed for reuse, redistribution, or production deployment.
