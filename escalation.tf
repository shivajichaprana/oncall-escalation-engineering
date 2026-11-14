variable "escalation_policies" {
  description = "Escalation steps by receiver, with minutes measured from the initial notification."
  type = map(list(object({
    after_minutes = number
    rotation      = string
  })))
  nullable = false
  default  = {}

  validation {
    condition = alltrue([
      for steps in values(var.escalation_policies) : try(
        steps[0].after_minutes == 0 &&
        length(distinct([for step in steps : step.rotation])) == length(steps) &&
        alltrue([
          for index, step in steps :
          step.after_minutes >= 0 && floor(step.after_minutes) == step.after_minutes &&
          (index == 0 ? true : step.after_minutes > steps[index - 1].after_minutes) &&
          can(regex("^[a-z][a-z0-9-]{0,62}$", step.rotation))
        ]),
        false
      )
    ])
    error_message = "Start every policy at zero minutes, then use strictly increasing whole-minute offsets and distinct rotation names."
  }
}

locals {
  escalation_rotations = toset(flatten([
    for steps in values(var.escalation_policies) : try(
      [for step in steps : step.rotation if try(step.rotation != null, false)], []
    )
  ]))
}

output "escalation_policies" {
  description = "Ordered escalation steps for a notification consumer, keyed by Alertmanager receiver."
  value       = var.escalation_policies

  precondition {
    condition     = length(setsubtract(toset(keys(var.escalation_policies)), toset(keys(var.destinations)))) == 0
    error_message = "Escalation policy keys must be declared Alertmanager receivers."
  }

  precondition {
    condition     = length(setsubtract(local.escalation_rotations, toset(keys(var.rotations)))) == 0
    error_message = "Every escalation step must refer to a defined rotation."
  }
}
