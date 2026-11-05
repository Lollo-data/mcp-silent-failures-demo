#!/usr/bin/env bash
# Start a local ClickHouse server without Docker.
# Binary and data stay in .clickhouse/, which git ignores.
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)/.clickhouse"
mkdir -p "$DIR"
cd "$DIR"

if [ ! -x ./clickhouse ]; then
  curl -fsSL https://clickhouse.com/ | sh
fi

exec ./clickhouse server
