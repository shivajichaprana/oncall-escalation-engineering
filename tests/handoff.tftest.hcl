run "handoff_export_preserves_schedule_contract" {
  command = plan

  variables {
    rotations = {
      primary = {
        start       = "2026-01-05T09:00:00Z"
        shift_hours = 168
        shift_count = 2
        responders  = ["engineer-a", "engineer-b"]
      }
    }
  }

  assert {
    condition = (
      output.handoff_context.schedules == output.oncall_schedules &&
      output.handoff_context.schedules.primary[0].responder == "engineer-a" &&
      output.handoff_context.schedules.primary[1].responder == "engineer-b" &&
      output.handoff_context.schedules.primary[0].ends_at == "2026-01-12T09:00:00Z"
    )
    error_message = "The handoff export must preserve the existing rotation windows and responder IDs."
  }
}
