# DNS and TLS Setup

## Required public hostname

A Prospect Dominion pilot requires a stable public hostname such as:

```text
pilot.customer.example
```

The hostname must resolve to the deployment host and be used consistently in:

- `PUBLIC_BASE_URL`
- `PD_PUBLIC_HOST`
- Caddy configuration
- webhook callback URL
- customer branding and documentation

## DNS records

Create the required A/AAAA record for the public hostname. The host should not expose Postgres, Redis, or internal service ports directly to the public internet.

Example:

```text
pilot.customer.example  A  203.0.113.20
```

## TLS termination

TLS must terminate at a public reverse proxy or Caddy before the API. Caddy is the supported repo path for this deployment.

Production requires:

- HTTPS only
- valid public certificate issuance and renewal
- trusted origin handling in the application runtime
- customer-managed DNS ownership and certificate validity checks

## Production expectations

The application must be configured to reject any missing or invalid hostname configuration. In production, `PUBLIC_BASE_URL` must use HTTPS and `PD_PUBLIC_HOST` must match the hostname parsed from that URL. The validator checks this condition before startup.

## Webhook URL

The public base URL must be the exact origin that receives Resend callbacks. The webhook URL must be part of the same TLS-protected host and must not point to a local or placeholder domain.

## Failure modes

Do not proceed with customer data if:

- DNS is not resolving
- TLS is not valid
- Caddy is not selected via `PD_CADDYFILE`
- the callback URL is not on the public HTTPS origin
- the app is running on a non-HTTPS hostname

## Minimum operational requirement

A pilot deployment is considered incomplete until the hostname resolves, the certificate is valid, and the Resend webhook endpoint is verified on the final public host.
