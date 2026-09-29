-- There is exactly one first-owner bootstrap per single-tenant pilot database.
CREATE TABLE IF NOT EXISTS bootstrap_guard (
  id BOOLEAN PRIMARY KEY DEFAULT true CHECK (id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
