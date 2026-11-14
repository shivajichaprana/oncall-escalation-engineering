variable "rotations" {
  description = "Named rotations with a UTC anchor, fixed shift duration and a finite number of shifts."
  type = map(object({
    start       = string
    shift_hours = number
    shift_count = number
    responders  = list(string)
  }))
  nullable = false
  default  = {}

  validation {
    condition = alltrue([
      for name, rotation in var.rotations : try(
        can(regex("^[a-z][a-z0-9-]{0,62}$", name)) &&
        can(regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$", rotation.start)) &&
        can(timeadd(rotation.start, "0h")) &&
        rotation.shift_hours >= 1 && rotation.shift_hours <= 168 &&
        floor(rotation.shift_hours) == rotation.shift_hours &&
        rotation.shift_count >= 1 && rotation.shift_count <= 366 &&
        floor(rotation.shift_count) == rotation.shift_count &&
        length(rotation.responders) > 0 &&
        length(distinct(rotation.responders)) == length(rotation.responders) &&
        alltrue([for id in rotation.responders : can(regex("^[a-z][a-z0-9-]{0,62}$", id))]),
        false
      )
    ])
    error_message = "Use named rotations with RFC3339 UTC anchors, 1–168 whole hours per shift, 1–366 shifts, and distinct responder IDs."
  }
}

locals {
  # Guard generation so malformed inputs receive the variable diagnostic.
  oncall_schedules = {
    for name, rotation in var.rotations : name => try([
      for index in range(rotation.shift_count) : {
        starts_at = timeadd(rotation.start, format("%dh", index * rotation.shift_hours))
        ends_at   = timeadd(rotation.start, format("%dh", (index + 1) * rotation.shift_hours))
        responder = rotation.responders[index % length(rotation.responders)]
      }
    ], []) if try(rotation.shift_count > 0 && rotation.shift_count <= 366, false)
  }
}

output "oncall_schedules" {
  description = "Finite UTC shift windows keyed by rotation. Start is inclusive and end is exclusive."
  value       = local.oncall_schedules
}
