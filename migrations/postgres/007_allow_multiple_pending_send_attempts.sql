ALTER TABLE send_attempts
  DROP CONSTRAINT IF EXISTS send_attempts_tenant_id_provider_provider_message_id_key;

ALTER TABLE send_attempts
  ADD CONSTRAINT send_attempts_tenant_id_provider_provider_message_id_key
  UNIQUE (tenant_id, provider, provider_message_id);
