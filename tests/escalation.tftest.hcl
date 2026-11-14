variables {
  rotations = {
    primary = {
      start       = "2026-01-05T09:00:00Z"
      shift_hours = 24
      shift_count = 3
      responders  = ["engineer-a", "engineer-b"]
    }
    backup = {
      start       = "2026-01-05T09:00:00Z"
      shift_hours = 24
      shift_count = 3
      responders  = ["engineer-c"]
    }
  }
}

run "renders_seamless_shifts_and_ordered_escalation" {
  command = plan

  variables {
    escalation_policies = {
      "primary-oncall" = [
        { after_minutes = 0, rotation = "primary" },
        { after_minutes = 10, rotation = "backup" },
      ]
    }
  }

  assert {
    condition = (
      join(",", output.oncall_schedules.primary[*].responder) == "engineer-a,engineer-b,engineer-a" &&
      output.oncall_schedules.primary[0].starts_at == "2026-01-05T09:00:00Z" &&
      output.oncall_schedules.primary[0].ends_at == output.oncall_schedules.primary[1].starts_at &&
      output.oncall_schedules.primary[1].ends_at == output.oncall_schedules.primary[2].starts_at &&
      output.oncall_schedules.primary[2].ends_at == "2026-01-08T09:00:00Z"
    )
    error_message = "Shifts must wrap through the responders and meet at UTC handoffs without overlap."
  }

  assert {
    condition = (
      output.escalation_policies["primary-oncall"][0].rotation == "primary" &&
      output.escalation_policies["primary-oncall"][1].rotation == "backup" &&
      output.escalation_policies["primary-oncall"][1].after_minutes == 10
    )
    error_message = "Escalation must preserve rotation order and offsets."
  }
}

run "rejects_undefined_rotation" {
  command = plan
  variables {
    escalation_policies = {
      "primary-oncall" = [{ after_minutes = 0, rotation = "missing" }]
    }
  }
  expect_failures = [output.escalation_policies]
}

run "rejects_undefined_receiver" {
  command = plan
  variables {
    escalation_policies = {
      "missing-receiver" = [{ after_minutes = 0, rotation = "primary" }]
    }
  }
  expect_failures = [output.escalation_policies]
}

run "rejects_duplicate_delay" {
  command = plan
  variables {
    escalation_policies = {
      "primary-oncall" = [
        { after_minutes = 0, rotation = "primary" },
        { after_minutes = 0, rotation = "backup" },
      ]
    }
  }
  expect_failures = [var.escalation_policies]
}

run "rejects_empty_roster" {
  command = plan
  variables {
    rotations = {
      primary = {
        start       = "2026-01-05T09:00:00Z"
        shift_hours = 24
        shift_count = 3
        responders  = []
      }
    }
  }
  expect_failures = [var.rotations]
}

run "rejects_non_utc_anchor" {
  command = plan
  variables {
    rotations = {
      primary = {
        start       = "2026-01-05T14:30:00+05:30"
        shift_hours = 24
        shift_count = 3
        responders  = ["engineer-a"]
      }
    }
  }
  expect_failures = [var.rotations]
}

run "rejects_null_step" {
  command = plan
  variables {
    escalation_policies = {
      "primary-oncall" = [null]
    }
  }
  expect_failures = [var.escalation_policies]
}
