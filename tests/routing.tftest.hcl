run "default_routes_cover_supported_severities" {
  command = plan

  assert {
    condition = [
      for route in yamldecode(output.alertmanager_yaml).route.routes :
      [route.matchers[0], route.receiver, tostring(route.continue)]
      ] == [
      ["severity=\"critical\"", "primary-oncall", "false"],
      ["severity=\"warning\"", "team-triage", "false"],
      ["severity=\"info\"", "service-inbox", "false"]
    ]
    error_message = "Each supported severity must match exactly one receiver."
  }

  assert {
    condition = (
      yamldecode(output.alertmanager_yaml).route.receiver == "unclassified"
      && !contains(keys(yamldecode(output.alertmanager_yaml).route), "matchers")
    )
    error_message = "An unconditional root route must catch missing or unknown severities."
  }

  assert {
    condition = alltrue([
      for receiver in yamldecode(output.alertmanager_yaml).receivers :
      length(receiver.webhook_configs) == 1 &&
      toset(keys(receiver.webhook_configs[0])) == toset(["send_resolved", "url_file"]) &&
      receiver.webhook_configs[0].send_resolved
    ])
    error_message = "Receivers must use runtime URL files and deliver recovery notifications."
  }
}

run "custom_destinations_can_share_a_receiver" {
  command = plan

  variables {
    destinations = {
      "team-inbox" = "/etc/alertmanager/urls/team"
      triage       = "/etc/alertmanager/urls/triage"
    }
    severity_destinations = {
      critical = "team-inbox"
      warning  = "team-inbox"
      info     = "triage"
    }
    fallback_destination = "triage"
  }

  assert {
    condition = (
      yamldecode(output.alertmanager_yaml).route.receiver == "triage"
      && yamldecode(output.alertmanager_yaml).route.routes[0].receiver == "team-inbox"
      && yamldecode(output.alertmanager_yaml).route.routes[1].receiver == "team-inbox"
    )
    error_message = "A shared receiver and custom fallback must survive rendering."
  }
}

run "reject_missing_severity" {
  command = plan
  variables {
    severity_destinations = {
      critical = "primary-oncall"
      warning  = "team-triage"
    }
  }
  expect_failures = [var.severity_destinations]
}

run "reject_unknown_fallback" {
  command = plan
  variables {
    fallback_destination = "undeclared"
  }
  expect_failures = [output.alertmanager_yaml]
}

run "reject_unknown_severity_receiver" {
  command = plan
  variables {
    severity_destinations = {
      critical = "undeclared"
      warning  = "team-triage"
      info     = "service-inbox"
    }
  }
  expect_failures = [output.alertmanager_yaml]
}

run "reject_inline_urls" {
  command = plan
  variables {
    destinations = merge({
      for name in ["primary-oncall", "team-triage", "service-inbox", "unclassified"] :
      name => "/etc/alertmanager/urls/receiver"
    }, { "primary-oncall" = "https://receiver.example.invalid/alerts" })
  }
  expect_failures = [var.destinations]
}
