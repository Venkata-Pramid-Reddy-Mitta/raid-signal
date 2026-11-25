.PHONY: install lint test experiments receipts report diagrams verify clean data

PY ?= python3

install:
	$(PY) -m pip install -e ".[dev]"

lint:
	ruff check src tools tests experiments

# Tests run as their own step with machine-readable reports, so a red test
# surfaces here and not as a traceback from the metrics collector.
test:
	$(PY) -m pytest --junitxml=reports/junit.xml \
		--cov=raid_signal --cov-report=json:coverage.json \
		--cov-report=term-missing -q

experiments:
	$(PY) experiments/exp01_lead_time.py
	$(PY) experiments/exp02_false_alarms.py
	$(PY) experiments/exp03_run_rules_vs_3sigma.py
	$(PY) experiments/exp04_lcl_blindness.py

# Re-measure every figure from the reports and the experiments, then fail if any
# document quotes a figure the code no longer produces.
receipts:
	$(PY) tools/collect_metrics.py --skip-tests
	$(PY) tools/check_numbers.py

report:
	raid-signal data/raid_log.csv --escalations data/escalations.csv --report docs/report.html

data:
	$(PY) tools/generate_data.py

# The one command the README promises a reviewer. Must pass from a fresh clone
# with no network.
verify: lint test receipts

clean:
	rm -rf reports coverage.json .coverage .pytest_cache .ruff_cache docs/report.html
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
