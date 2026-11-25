.DEFAULT_GOAL := validate

PYTHON ?= python3
VAR_FILE ?= rotations/example.tfvars.example
OUTPUT ?= build/alertmanager.yml

export PYTHON VAR_FILE OUTPUT
export CHECKPOINT_DISABLE := 1
export TF_IN_AUTOMATION := 1

.PHONY: init validate simulate deploy

init:
	@terraform init -backend=false -input=false -no-color

validate: init
	@terraform fmt -check -recursive
	@terraform validate -no-color
	@terraform test -no-color
	@"$$PYTHON" -m pytest -m "not routing"
	@"$$PYTHON" -m ruff check .
	@"$$PYTHON" -m ruff format --check .
	@"$$PYTHON" -m mypy --strict quality handoff

simulate: init
	@command -v terraform >/dev/null
	@command -v amtool >/dev/null
	@"$$PYTHON" -m pytest -m routing --strict-markers

# Prepare a validated local artifact for the owning team's service review.
deploy: validate simulate
	@set -eu; \
	umask 077; \
	temp="$$(mktemp -d)"; candidate=""; \
	trap 'rm -rf "$$temp"; if test -n "$$candidate"; then rm -f "$$candidate"; fi' EXIT HUP INT TERM; \
	mkdir -p "$$(dirname "$$OUTPUT")"; \
	candidate="$$(mktemp "$$OUTPUT.tmp.XXXXXX")"; \
	terraform plan -refresh=false -input=false -no-color \
	  -var-file="$$VAR_FILE" -out="$$temp/config.tfplan"; \
	terraform show -json "$$temp/config.tfplan" > "$$temp/plan.json"; \
	"$$PYTHON" -c 'import json, sys; print(json.load(sys.stdin)["planned_values"]["outputs"]["alertmanager_yaml"]["value"], end="")' \
	  < "$$temp/plan.json" > "$$candidate"; \
	amtool check-config "$$candidate"; \
	mv -f "$$candidate" "$$OUTPUT"; candidate=""; \
	printf 'Staged validated configuration at %s\n' "$$OUTPUT"
