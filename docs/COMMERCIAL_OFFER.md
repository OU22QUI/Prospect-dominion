# Aethonex Prospect Dominion Deployment

## What is being sold

Prospect Dominion is an MIT-licensed, self-hostable Core. Aethonex does not sell exclusive access to that source code: anyone may use, modify, and redistribute the Core under the MIT License.

The current paid path is an implementation engagement around the Core, not a separate paid software edition. The customer pays for scoped delivery in their environment: configuring and validating a bounded workflow, integrating agreed inputs and outputs, setting up human approval and operating controls, documenting the deployment, and handing it over.

Other Aethonex products are separate and are not included in or integrated with this engagement. Prospect Intelligence OS is a separate Apache-2.0 project; Dominion does not currently import its `dossier_v1` format.

## Initial engagement scope

Each engagement must be scoped and accepted in writing before work starts. The current pilot-sized baseline is:

- one customer-controlled environment and one workspace
- up to five named users and approximately 200 target accounts
- one bounded workflow and one or two agreed input sources
- signal intake, prioritization, a human approval step, the approved action, and outcome recording
- deployment configuration, verification, operator documentation, and handover

These are planning limits, not a promise that every source, provider, environment, or workflow is already supported. Confirm feasibility for the customer's actual systems before agreeing to scope.

## Delivery and acceptance

The statement of work should identify the selected workflow, data sources, providers, customer responsibilities, exclusions, schedule, price, and change-control process. Acceptance should be based on observable checks agreed before implementation, including:

1. the agreed input is ingested and its provenance can be inspected;
2. prioritization produces an explainable result;
3. a proposed action cannot proceed without the configured human approval;
4. the approved action and provider response or test result are recorded;
5. failure, retry, and pause behavior is demonstrated for the scoped path;
6. deployment, backup/restore, and operator handover checks are completed in the target environment.

Use synthetic data and a controlled test provider for demonstrations. A live provider or customer-data rehearsal requires explicit customer approval and the security and deployment prerequisites in [Product Status](PRODUCT_STATUS.md).

## Commercial terms

There is no published standard price, subscription, or customer license grant in this repository. Provide a written proposal and signed agreement that define price, payment schedule, delivery dates, support, update commitments, data handling, and the customer's rights to the Core and any separately delivered work. Do not describe the MIT Core as exclusive, or imply that buying an implementation service changes the MIT license.

Do not promise ongoing managed operation or recurring support until the support scope and delivery economics are agreed in writing.

## Future paid software modules

No proprietary Dominion module or paid self-hosted edition is currently shipped. Potential future modules may be built only when there is validated customer demand and a clear technical boundary. Before selling any such module, publish its included capabilities, prerequisites, compatibility, support policy, and license terms; keep the MIT Core independently useful and usable without it.

## Relationship to other Aethonex repositories

| Project | Current role | Relationship to this engagement |
|---|---|---|
| Prospect Dominion | MIT-licensed governed workflow Core | The software deployed and configured for the engagement |
| Prospect Intelligence OS | Separate Apache-2.0 public-data research project | Not integrated with Dominion; `dossier_v1` import is not included |

The engagement is an implementation service around the MIT Core, not a sale of or claim to integrate other Aethonex products.
