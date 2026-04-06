#!/usr/bin/env bash
# =============================================================================
# Security Fuzzing Orchestrator
#
# Runs all security testing layers:
#   1. Bandit — Python static security analysis
#   2. pip-audit — dependency vulnerability scan
#   3. Hypothesis — property-based SDK/CLI fuzzing (no Docker needed)
#   4. JSON-RPC API fuzzing — against live Dockerized Kanboard
#
# Usage:
#   ./scripts/security-fuzz.sh              # run all layers
#   ./scripts/security-fuzz.sh --no-docker  # skip API fuzzing (layers 1-3 only)
#   ./scripts/security-fuzz.sh --api-only   # skip Python-native, run API fuzz only
#
# Reports are written to reports/security/
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_DIR="$PROJECT_ROOT/reports/security"

NO_DOCKER=false
API_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --no-docker) NO_DOCKER=true ;;
        --api-only)  API_ONLY=true ;;
        -h|--help)
            echo "Usage: $0 [--no-docker] [--api-only]"
            echo ""
            echo "  --no-docker  Skip API fuzzing (Bandit + pip-audit + Hypothesis only)"
            echo "  --api-only   Skip Python-native tests (API fuzzing only)"
            exit 0
            ;;
    esac
done

mkdir -p "$REPORT_DIR"
cd "$PROJECT_ROOT"

OVERALL_EXIT=0
SUMMARY=""

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
run_step() {
    local name="$1"
    shift
    echo ""
    echo "================================================================="
    echo "  $name"
    echo "================================================================="
    echo ""
    if "$@"; then
        SUMMARY="$SUMMARY  ✅ $name\n"
    else
        SUMMARY="$SUMMARY  ❌ $name (exit $?)\n"
        OVERALL_EXIT=1
    fi
}

# ---------------------------------------------------------------------------
# 1. Bandit — Python static security analysis
# ---------------------------------------------------------------------------
if [ "$API_ONLY" = false ]; then

    run_step "Bandit (Python static security analysis)" \
        python -m bandit \
            -r src/ \
            -f json \
            -o "$REPORT_DIR/bandit-report.json" \
            --severity-level medium \
            --confidence-level medium \
            -x "tests/" \
            || true  # bandit exits non-zero on findings; we parse the report

    # Also produce a human-readable report
    python -m bandit \
        -r src/ \
        -f txt \
        --severity-level medium \
        --confidence-level medium \
        -x "tests/" \
        > "$REPORT_DIR/bandit-report.txt" 2>&1 || true

    echo "  → Reports: $REPORT_DIR/bandit-report.{json,txt}"

    # Check if there are high-severity findings
    if [ -f "$REPORT_DIR/bandit-report.json" ]; then
        HIGH_COUNT=$(python -c "
import json, sys
try:
    data = json.load(open('$REPORT_DIR/bandit-report.json'))
    results = data.get('results', [])
    high = [r for r in results if r.get('issue_severity') == 'HIGH']
    print(len(high))
except Exception:
    print(0)
" 2>/dev/null || echo "0")
        if [ "$HIGH_COUNT" -gt 0 ]; then
            echo "  ⚠️  $HIGH_COUNT HIGH severity findings in Bandit report"
        fi
    fi

fi

# ---------------------------------------------------------------------------
# 2. pip-audit — dependency vulnerability scan
# ---------------------------------------------------------------------------
if [ "$API_ONLY" = false ]; then

    run_step "pip-audit (dependency vulnerability scan)" \
        python -m pip_audit \
            --format json \
            --output "$REPORT_DIR/pip-audit-report.json" \
            --desc \
            || true

    # Human-readable too
    python -m pip_audit --desc > "$REPORT_DIR/pip-audit-report.txt" 2>&1 || true

    echo "  → Reports: $REPORT_DIR/pip-audit-report.{json,txt}"

fi

# ---------------------------------------------------------------------------
# 3. Hypothesis — property-based SDK/CLI fuzzing
# ---------------------------------------------------------------------------
if [ "$API_ONLY" = false ]; then

    run_step "Hypothesis (property-based SDK/CLI fuzz testing)" \
        python -m pytest \
            tests/security/test_sdk_fuzz.py \
            -v \
            -m security \
            --tb=short \
            --junit-xml="$REPORT_DIR/hypothesis-results.xml" \
            --no-header

fi

# ---------------------------------------------------------------------------
# 4. JSON-RPC API fuzzing (requires Docker)
# ---------------------------------------------------------------------------
if [ "$NO_DOCKER" = false ]; then

    # Check Docker availability
    if ! docker info &>/dev/null; then
        echo ""
        echo "⚠️  Docker not available — skipping API fuzzing."
        echo "   Run with Docker Desktop started, or use --no-docker."
        SUMMARY="$SUMMARY  ⏭️  API Fuzzing (Docker unavailable)\n"
    else
        run_step "JSON-RPC API fuzzing (against Docker Kanboard)" \
            python -m pytest \
                tests/security/test_jsonrpc_fuzz.py \
                -v \
                -m security \
                --tb=short \
                --junit-xml="$REPORT_DIR/api-fuzz-results.xml" \
                --no-header
    fi

fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "================================================================="
echo "  Security Fuzz Summary"
echo "================================================================="
echo -e "$SUMMARY"
echo "Reports: $REPORT_DIR/"
ls -la "$REPORT_DIR/" 2>/dev/null || true
echo ""

exit $OVERALL_EXIT
