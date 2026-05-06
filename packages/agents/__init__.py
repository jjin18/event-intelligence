"""
Pipeline agents for Eventful.

Stages used by `run_intelligence`: objective → audience → sourcing →
room_balance, plus rule-based scoring in `packages.scoring.attendee_fit`.

Additional connectors (calendar, CRM, email, etc.) should be added as thin
tool modules and invoked from an orchestration layer—not duplicated here.
"""
