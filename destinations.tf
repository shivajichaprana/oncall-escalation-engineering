variable "destinations" {
  description = "Receiver names mapped to absolute runtime files containing webhook URLs."
  type        = map(string)
  nullable    = false
  default = {
    "primary-oncall" = "/etc/alertmanager/webhooks/primary-oncall"
    "team-triage"    = "/etc/alertmanager/webhooks/team-triage"
    "service-inbox"  = "/etc/alertmanager/webhooks/service-inbox"
    "unclassified"   = "/etc/alertmanager/webhooks/unclassified"
  }

  validation {
    condition = length(var.destinations) > 0 && alltrue([
      for name, path in var.destinations :
      can(regex("^[a-z][a-z0-9-]{0,62}$", name)) &&
      can(regex("^(/[A-Za-z0-9_-][A-Za-z0-9_.-]*)+$", path))
    ])
    error_message = "Define at least one lowercase receiver name and use absolute URL file paths with valid path components."
  }
}

locals {
  alertmanager_receivers = [
    for name, path in var.destinations : {
      name = name
      webhook_configs = [{
        url_file      = path
        send_resolved = true
      }]
    }
  ]
}
