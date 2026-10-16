"""Namespace-scoped demonstration reset; never drops databases or volumes."""

import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from packages.domain.demo_reset import reset_dataset
from packages.domain.demo import DATASET
from services.api.store import engine

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--dataset", choices=[DATASET], required=True)
parser.add_argument("--apply", action="store_true")
args = parser.parse_args()
with engine.begin() as conn:
    count = reset_dataset(conn, args.dataset, apply=args.apply)
print(
    ("Removed" if args.apply else "Preflight passed for")
    + " "
    + str(count)
    + " namespace-owned resources. User-owned resources and files retained."
)
