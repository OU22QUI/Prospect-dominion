ALTER TABLE bootstrap_guard
  ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id);

UPDATE bootstrap_guard
SET tenant_id = (SELECT id FROM tenants ORDER BY created_at, id LIMIT 1)
WHERE id = true AND tenant_id IS NULL;