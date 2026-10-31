ALTER TABLE send_attempts
  DROP CONSTRAINT IF EXISTS send_attempts_status_check;

ALTER TABLE send_attempts
  ADD CONSTRAINT send_attempts_status_check
  CHECK (status IN ('queued', 'sent', 'delivered', 'bounced', 'complained', 'replied', 'failed', 'suppressed', 'simulated'));

ALTER TABLE action_feedback
  DROP CONSTRAINT IF EXISTS action_feedback_feedback_type_check;

ALTER TABLE action_feedback
  ADD CONSTRAINT action_feedback_feedback_type_check
  CHECK (feedback_type IN ('approved', 'rejected', 'sent', 'delivered', 'bounced', 'complained', 'replied', 'suppressed', 'failed', 'simulated'));
