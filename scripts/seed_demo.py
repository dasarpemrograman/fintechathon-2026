"""Seed synthetic local fixtures; credentials and live services are not needed."""

import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from packages.domain.demo import seed, analyze_seeded
from services.worker.jobs import run_once

p = argparse.ArgumentParser()
p.add_argument("--reference-date")
args = p.parse_args()
from scripts.verify_fixture_assets import verify

verify()
result = seed(args.reference_date)
from packages.domain.demo_stages import seed_stages, seed_sandbox_plans, drain

drain()
analyze_seeded()
drain()
seed_sandbox_plans()
result["checkpoints"] = seed_stages()
print(json.dumps(result, indent=2))
