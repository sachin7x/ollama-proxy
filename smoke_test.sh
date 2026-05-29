#!/usr/bin/env bash
# smoke_test.sh — hit every endpoint while the server is running on :11434
# Usage: bash smoke_test.sh
set -euo pipefail

BASE="http://localhost:11434"
PASS=0; FAIL=0

check() {
    local label="$1" expected="$2" actual="$3"
    if echo "$actual" | grep -q "$expected"; then
        echo "  PASS  $label"
        PASS=$((PASS+1))
    else
        echo "  FAIL  $label"
        echo "        expected: $expected"
        echo "        got:      $(echo "$actual" | head -c 120)"
        FAIL=$((FAIL+1))
    fi
}

echo ""
echo "=== ollama-proxy smoke tests (server must be running on :11434) ==="
echo ""

# Health
check "GET /  (plain text)"   "Ollama is running" \
    "$(curl -s $BASE/)"

check "GET /api/version"       '"version"' \
    "$(curl -s $BASE/api/version)"

# Model listing
check "GET /api/tags"          '"models"' \
    "$(curl -s $BASE/api/tags)"

check "GET /api/ps"            '"models":[]' \
    "$(curl -s $BASE/api/ps)"

# Show
check "POST /api/show (known)" '"capabilities"' \
    "$(curl -s -X POST $BASE/api/show -H 'Content-Type: application/json' -d '{"model":"openai/gpt-4o"}')"

check "POST /api/show (unknown) -> 404" '"error"' \
    "$(curl -s -X POST $BASE/api/show -H 'Content-Type: application/json' -d '{"model":"fake/nope"}')"

# Model management mocks
check "POST /api/pull (stream)" '"success"' \
    "$(curl -s -X POST $BASE/api/pull -H 'Content-Type: application/json' -d '{"model":"openai/gpt-4o"}')"

check "DELETE /api/delete"     '' \
    "$(curl -s -X DELETE $BASE/api/delete -H 'Content-Type: application/json' -d '{"model":"openai/gpt-4o"}')"

check "POST /api/copy"         '' \
    "$(curl -s -X POST $BASE/api/copy -H 'Content-Type: application/json' -d '{"source":"a","destination":"b"}')"

check "POST /api/push -> 501"  '"error"' \
    "$(curl -s -X POST $BASE/api/push -H 'Content-Type: application/json' -d '{"model":"openai/gpt-4o"}')"

check "POST /api/create -> 501" '"error"' \
    "$(curl -s -X POST $BASE/api/create -H 'Content-Type: application/json' -d '{"model":"x"}')"

# Unknown provider -> 400
check "POST /api/chat unknown provider -> 400" '"error"' \
    "$(curl -s -X POST $BASE/api/chat -H 'Content-Type: application/json' \
       -d '{"model":"badprovider/x","messages":[{"role":"user","content":"hi"}]}')"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ $FAIL -eq 0 ] && echo "All smoke tests passed!" || echo "Some tests failed - check server logs."
