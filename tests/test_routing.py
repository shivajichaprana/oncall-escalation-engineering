"""Validate Terraform-rendered routes with Alertmanager's own offline evaluator.

Run with terraform and amtool on PATH. Missing tools skip these integration
cases in a Python-only environment. The routing CI job requires both tools.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.routing


@pytest.fixture(scope="module", params=["defaults", "custom"])
def rendered_routes(request, tmp_path_factory):
    terraform = shutil.which("terraform")
    amtool = shutil.which("amtool")
    if terraform is None or amtool is None:
        pytest.skip("Offline routing integration requires terraform and amtool on PATH.")
    root = Path(__file__).resolve().parents[1]
    folder = tmp_path_factory.mktemp(request.param)
    expected = {
        "critical": "primary-oncall",
        "warning": "team-triage",
        "info": "service-inbox",
        "fallback": "unclassified",
    }
    variables = {}
    if request.param == "custom":
        expected = {
            "critical": "incident-team",
            "warning": "incident-team",
            "info": "triage",
            "fallback": "triage",
        }
        variables = {
            "destinations": {
                "incident-team": "/etc/alertmanager/urls/incident",
                "triage": "/etc/alertmanager/urls/triage",
            },
            "severity_destinations": {k: v for k, v in expected.items() if k != "fallback"},
            "fallback_destination": expected["fallback"],
        }
    var_file = folder / "routing.tfvars.json"
    var_file.write_text(json.dumps(variables))
    plan = folder / "routes.tfplan"
    subprocess.run(
        [
            terraform,
            "plan",
            "-refresh=false",
            "-input=false",
            "-no-color",
            f"-var-file={var_file}",
            f"-out={plan}",
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = subprocess.run(
        [terraform, "show", "-json", str(plan)],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    config = folder / "alertmanager.yml"
    config.write_text(
        json.loads(output.stdout)["planned_values"]["outputs"]["alertmanager_yaml"]["value"]
    )
    subprocess.run(
        [amtool, "check-config", str(config), "--enable-feature=utf8-strict-mode"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return amtool, config, expected


@pytest.mark.parametrize(
    ("labels", "destination"),
    [
        (["severity=critical"], "critical"),
        (["severity=warning"], "warning"),
        (["severity=info"], "info"),
        ([], "fallback"),
        (["severity=CRITICAL"], "fallback"),
        (["severity=critical-extra"], "fallback"),
        (["severity=critical", "service=example-service"], "critical"),
    ],
)
def test_actual_route_resolution(rendered_routes, labels, destination):
    amtool, config, expected = rendered_routes
    result = subprocess.run(
        [
            amtool,
            "config",
            "routes",
            "test",
            f"--config.file={config}",
            f"--verify.receivers={expected[destination]}",
            "alertname=ExampleAlert",
            *labels,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.stdout.strip().splitlines() == [expected[destination]]
