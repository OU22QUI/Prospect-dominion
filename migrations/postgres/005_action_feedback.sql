CREATE TABLE IF NOT EXISTS action_feedback (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  approval_id UUID REFERENCES approvals(id),
  send_attempt_id UUID REFERENCES send_attempts(id),
  thread_id TEXT NOT NULL,
  account_id TEXT,
  feedback_type TEXT NOT NULL CHECK (feedback_type IN ('approved', 'rejected', 'sent', 'delivered', 'bounced', 'complained', 'replied', 'suppressed', 'failed')),
  details JSONB NOT NULL DEFAULT '{}'::jsonb,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (tenant_id, thread_id) REFERENCES threads(tenant_id, thread_id),
  FOREIGN KEY (tenant_id, account_id) REFERENCES accounts(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS action_feedback_tenant_time_idx ON action_feedback (tenant_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS action_feedback_account_idx ON action_feedback (tenant_id, account_id, feedback_type);
