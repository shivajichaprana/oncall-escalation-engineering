output "handoff_context" {
  description = "Schedule context for the local handoff report CLI. Export the planned output as JSON."
  value = {
    schedules = local.oncall_schedules
  }
}
