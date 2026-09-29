CREATE TABLE IF NOT EXISTS workspace_settings (
  tenant_id UUID PRIMARY KEY REFERENCES tenants(id),
  icp_rules JSONB NOT NULL DEFAULT '{"version":1,"base_score":0,"rules":[]}'::jsonb,
  approval_policy JSONB NOT NULL DEFAULT '{"require_approval":true}'::jsonb,
  updated_by UUID REFERENCES users(id),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS account_scores (
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  account_id TEXT NOT NULL,
  score NUMERIC(7,3) NOT NULL,
  explanation JSONB NOT NULL,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, account_id),
  FOREIGN KEY (tenant_id, account_id) REFERENCES accounts(tenant_id, id)
);

CREATE TABLE IF NOT EXISTS recommended_actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  account_id TEXT NOT NULL,
  thread_id TEXT,
  action_type TEXT NOT NULL CHECK (action_type IN ('research', 'draft_outreach', 'request_intro', 'wait')),
  confidence NUMERIC(5,4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  rationale JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'superseded', 'completed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (tenant_id, account_id) REFERENCES accounts(tenant_id, id),
  FOREIGN KEY (tenant_id, thread_id) REFERENCES threads(tenant_id, thread_id)
);

CREATE TABLE IF NOT EXISTS suppression_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  email TEXT NOT NULL,
  reason TEXT NOT NULL,
  source TEXT NOT NULL,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  removed_at TIMESTAMPTZ,
  UNIQUE (tenant_id, email)
);

CREATE TABLE IF NOT EXISTS send_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  approval_id UUID NOT NULL REFERENCES approvals(id),
  thread_id TEXT NOT NULL,
  recipient_email TEXT NOT NULL,
  provider TEXT NOT NULL,
  provider_message_id TEXT,
  idempotency_key TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('queued', 'sent', 'delivered', 'bounced', 'complained', 'replied', 'failed', 'suppressed')),
  error_detail TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  sent_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (tenant_id, thread_id) REFERENCES threads(tenant_id, thread_id),
  UNIQUE (tenant_id, idempotency_key),
  UNIQUE NULLS NOT DISTINCT (tenant_id, provider, provider_message_id)
);

CREATE TABLE IF NOT EXISTS webhook_receipts (
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  provider TEXT NOT NULL,
  event_id TEXT NOT NULL,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  payload JSONB NOT NULL,
  PRIMARY KEY (tenant_id, provider, event_id)
);

CREATE TABLE IF NOT EXISTS ingest_failures (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  source_connection_id UUID NOT NULL REFERENCES source_connections(id),
  idempotency_key TEXT NOT NULL,
  row_number INTEGER,
  error_detail TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 1,
  next_retry_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at TIMESTAMPTZ,
  UNIQUE (tenant_id, source_connection_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS account_scores_queue_idx ON account_scores (tenant_id, score DESC, computed_at DESC);
CREATE INDEX IF NOT EXISTS recommended_actions_queue_idx ON recommended_actions (tenant_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS send_attempts_thread_idx ON send_attempts (tenant_id, thread_id, created_at DESC);
