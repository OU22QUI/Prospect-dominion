-- Pilot system-of-record schema. The API repository adapter and server-issued
-- identity layer are phased in next; this migration defines their constraints.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), slug TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE CHECK (name IN ('owner', 'operator', 'viewer')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), email TEXT NOT NULL UNIQUE,
  display_name TEXT, password_hash TEXT, is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS workspace_memberships (
  tenant_id UUID NOT NULL REFERENCES tenants(id), user_id UUID NOT NULL REFERENCES users(id),
  role_id UUID NOT NULL REFERENCES roles(id), created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
  PRIMARY KEY (tenant_id, user_id)
);
CREATE TABLE IF NOT EXISTS source_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID NOT NULL REFERENCES tenants(id),
  source_type TEXT NOT NULL, display_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'error', 'disabled')),
  config_ref TEXT, last_error TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
  UNIQUE (tenant_id, display_name)
);
CREATE TABLE IF NOT EXISTS sync_cursors (
  source_connection_id UUID PRIMARY KEY REFERENCES source_connections(id), cursor_value TEXT,
  last_success_at TIMESTAMPTZ, updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS accounts (
  tenant_id UUID NOT NULL REFERENCES tenants(id), id TEXT NOT NULL, domain TEXT NOT NULL,
  legal_name TEXT, display_name TEXT, industry TEXT, icp_score NUMERIC(5,4),
  enrichment JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
  PRIMARY KEY (tenant_id, id), UNIQUE (tenant_id, domain)
);
CREATE TABLE IF NOT EXISTS people (
  tenant_id UUID NOT NULL REFERENCES tenants(id), id TEXT NOT NULL, account_id TEXT,
  full_name TEXT, email TEXT, title TEXT, seniority TEXT, role_function TEXT, linkedin_url TEXT,
  psychographics JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, account_id) REFERENCES accounts(tenant_id, id)
);
CREATE TABLE IF NOT EXISTS threads (
  tenant_id UUID NOT NULL REFERENCES tenants(id), thread_id TEXT NOT NULL, person_id TEXT NOT NULL,
  account_id TEXT, campaign_id TEXT, opp_stage TEXT NOT NULL DEFAULT 'new', consent_basis TEXT NOT NULL DEFAULT 'none',
  next_action_at TIMESTAMPTZ, last_touch_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
  PRIMARY KEY (tenant_id, thread_id),
  FOREIGN KEY (tenant_id, person_id) REFERENCES people(tenant_id, id),
  FOREIGN KEY (tenant_id, account_id) REFERENCES accounts(tenant_id, id)
);
CREATE TABLE IF NOT EXISTS events (
  tenant_id UUID NOT NULL REFERENCES tenants(id), event_id TEXT NOT NULL, thread_id TEXT NOT NULL,
  event_type TEXT NOT NULL, source TEXT NOT NULL, source_connection_id UUID REFERENCES source_connections(id),
  external_id TEXT, raw_ref TEXT, payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(), idempotency_key TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY (tenant_id, event_id),
  FOREIGN KEY (tenant_id, thread_id) REFERENCES threads(tenant_id, thread_id),
  UNIQUE NULLS NOT DISTINCT (tenant_id, idempotency_key)
);
CREATE TABLE IF NOT EXISTS outcomes (
  tenant_id UUID NOT NULL REFERENCES tenants(id), outcome_id TEXT NOT NULL, thread_id TEXT NOT NULL,
  account_id TEXT, stage_from TEXT, stage_to TEXT NOT NULL, reason TEXT, value_amount NUMERIC(14,2),
  attributed_signal TEXT, occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, outcome_id), FOREIGN KEY (tenant_id, thread_id) REFERENCES threads(tenant_id, thread_id),
  FOREIGN KEY (tenant_id, account_id) REFERENCES accounts(tenant_id, id)
);
CREATE TABLE IF NOT EXISTS approvals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID NOT NULL REFERENCES tenants(id), thread_id TEXT NOT NULL,
  requested_by UUID REFERENCES users(id), decided_by UUID REFERENCES users(id),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'expired')),
  action_type TEXT NOT NULL, action_payload JSONB NOT NULL DEFAULT '{}'::jsonb, idempotency_key TEXT NOT NULL,
  decision_reason TEXT, expires_at TIMESTAMPTZ, requested_at TIMESTAMPTZ NOT NULL DEFAULT now(), decided_at TIMESTAMPTZ,
  FOREIGN KEY (tenant_id, thread_id) REFERENCES threads(tenant_id, thread_id), UNIQUE (tenant_id, idempotency_key)
);
CREATE TABLE IF NOT EXISTS audit_events (
  id BIGSERIAL PRIMARY KEY, tenant_id UUID NOT NULL REFERENCES tenants(id), actor_user_id UUID REFERENCES users(id),
  event_type TEXT NOT NULL, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, request_id UUID,
  details JSONB NOT NULL DEFAULT '{}'::jsonb, occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE OR REPLACE FUNCTION prevent_audit_mutation() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'audit_events is append-only'; END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS audit_events_immutable ON audit_events;
CREATE TRIGGER audit_events_immutable BEFORE UPDATE OR DELETE ON audit_events
FOR EACH ROW EXECUTE FUNCTION prevent_audit_mutation();
CREATE INDEX IF NOT EXISTS accounts_priority_idx ON accounts (tenant_id, icp_score DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS people_account_idx ON people (tenant_id, account_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS threads_stage_idx ON threads (tenant_id, opp_stage, updated_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS events_thread_time_idx ON events (tenant_id, thread_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS events_source_external_idx ON events (tenant_id, source, external_id);
CREATE INDEX IF NOT EXISTS approvals_queue_idx ON approvals (tenant_id, status, requested_at ASC);
CREATE INDEX IF NOT EXISTS audit_events_tenant_time_idx ON audit_events (tenant_id, occurred_at DESC);
INSERT INTO roles (name) VALUES ('owner'), ('operator'), ('viewer') ON CONFLICT (name) DO NOTHING;
