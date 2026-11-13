variable "severity_destinations" {
  description = "Receiver names for the three supported severity labels."
  type        = map(string)
  nullable    = false
  default = {
    critical = "primary-oncall"
    warning  = "team-triage"
    info     = "service-inbox"
  }

  validation {
    condition = toset(keys(var.severity_destinations)) == toset(["critical", "warning", "info"]) && alltrue([
      for name in values(var.severity_destinations) : can(regex("^[a-z][a-z0-9-]{0,62}$", name))
    ])
    error_message = "Map critical, warning, and info to receiver names. Use the fallback for other labels."
  }
}

variable "fallback_destination" {
  description = "Receiver for alerts whose severity is missing or unrecognised."
  type        = string
  nullable    = false
  default     = "unclassified"
}

locals {
  alertmanager_route = {
    receiver        = var.fallback_destination
    group_by        = ["alertname", "service", "severity"]
    group_wait      = "30s"
    group_interval  = "5m"
    repeat_interval = "4h"
    routes = [
      for severity in ["critical", "warning", "info"] : {
        receiver = lookup(var.severity_destinations, severity, var.fallback_destination)
        matchers = ["severity=\"${severity}\""]
        continue = false
      }
    ]
  }
}

output "alertmanager_yaml" {
  description = "Rendered routing and receivers for review before loading into Alertmanager."
  value = yamlencode({
    route     = local.alertmanager_route
    receivers = local.alertmanager_receivers
  })

  precondition {
    condition = length(setsubtract(
      toset(concat([var.fallback_destination], values(var.severity_destinations))),
      toset(keys(var.destinations))
    )) == 0
    error_message = "All severity and fallback routes must point to a declared receiver."
  }
}
