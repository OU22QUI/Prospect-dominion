#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

printf 'Stopping containers and removing volumes...\n'
docker compose down -v --remove-orphans

printf 'Resetting demo data...\n'
rm -f demo/data/synthetic_signals.csv

printf 'Demo reset complete.\n'
