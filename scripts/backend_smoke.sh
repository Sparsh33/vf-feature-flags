#!/usr/bin/env bash
# Backend end-to-end smoke test against docker-compose stack.
# Prints PASS/FAIL per step. Exits non-zero on any FAIL.

set -u
API="${API:-http://localhost:8000}"
EPOCH="$(date +%s)"
EMAIL="smoke+${EPOCH}@example.com"
PASSWORD="Password123!"
CLIENT_NAME="Smoke Co ${EPOCH}"
FLAG_KEY="smoke_flag_${EPOCH}"
PASS=0
FAIL=0

color() { printf '\033[%sm%s\033[0m' "$1" "$2"; }
pass() { PASS=$((PASS+1)); printf ' %s %s\n' "$(color '32' 'PASS')" "$1"; }
fail() { FAIL=$((FAIL+1)); printf ' %s %s\n    %s\n' "$(color '31' 'FAIL')" "$1" "$2"; }
section() { printf '\n%s %s\n' "$(color '36;1' '==')" "$1"; }

jqr() { echo "$1" | jq -r "$2"; }

# ---------------- 1. Health ----------------
section "1. Health"
H=$(curl -s "$API/health")
[ "$(jqr "$H" .status)" = "ok" ] && pass "GET /health → ok" || fail "GET /health" "$H"

# ---------------- 2-3. Signup + capture JWT/API key ----------------
section "2. Signup"
S=$(curl -s -X POST "$API/api/auth/signup" -H 'content-type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"client_name\":\"$CLIENT_NAME\"}")
JWT=$(jqr "$S" .access_token)
API_KEY=$(jqr "$S" .api_key)
CLIENT_ID=$(jqr "$S" .client.id)
USER_ID=$(jqr "$S" .user.id)
[ -n "$JWT" ] && [ "$JWT" != "null" ] && pass "POST /api/auth/signup → JWT + api_key" \
  || fail "signup" "$S"

# ---------------- 4. Login ----------------
section "3. Login"
L=$(curl -s -X POST "$API/api/auth/login" -H 'content-type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
JWT2=$(jqr "$L" .access_token)
[ -n "$JWT2" ] && [ "$JWT2" != "null" ] && pass "POST /api/auth/login → JWT" || fail "login" "$L"

section "4. /me"
M=$(curl -s "$API/api/auth/me" -H "authorization: Bearer $JWT")
[ "$(jqr "$M" .email)" = "$EMAIL" ] && pass "GET /api/auth/me → self" || fail "/me" "$M"

# ---------------- 5. Create flag ----------------
section "5. Create flag (cohorts sum=100)"
C=$(curl -s -X POST "$API/api/flags/" -H "authorization: Bearer $JWT" -H 'content-type: application/json' \
  -d "{
    \"flag_key\":\"$FLAG_KEY\",
    \"name\":\"Smoke Flag\",
    \"description\":\"e2e smoke\",
    \"default_value\":{\"mode\":\"off\"},
    \"cohorts\":[
      {\"id\":\"\",\"name\":\"control\",\"percentage\":60,\"value\":{\"variant\":\"control\"}},
      {\"id\":\"\",\"name\":\"treatment\",\"percentage\":40,\"value\":{\"variant\":\"treatment\"}}
    ]
  }")
FLAG_ID=$(jqr "$C" .id)
[ -n "$FLAG_ID" ] && [ "$FLAG_ID" != "null" ] && pass "POST /api/flags/ → created" || fail "create flag" "$C"

# ---------------- 6. Reject bad cohort sum ----------------
section "6. Cohort sum validation"
BAD=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/api/flags/" \
  -H "authorization: Bearer $JWT" -H 'content-type: application/json' \
  -d "{
    \"flag_key\":\"bad_${EPOCH}\",\"name\":\"x\",\"default_value\":null,
    \"cohorts\":[{\"id\":\"\",\"name\":\"a\",\"percentage\":50,\"value\":1}]
  }")
[ "$BAD" = "422" ] || [ "$BAD" = "400" ] && pass "cohorts sum!=100 → $BAD" || fail "cohort sum guard" "got $BAD"

# ---------------- 7. List ----------------
section "7. List flags"
LI=$(curl -s "$API/api/flags/" -H "authorization: Bearer $JWT")
N=$(jqr "$LI" '.flags | length')
[ "$N" -ge 1 ] && pass "GET /api/flags/ → $N flag(s)" || fail "list flags" "$LI"

# ---------------- 8. Evaluate 500× ----------------
section "8. Evaluate 500× via API key"
TMPD=$(mktemp -d)
TALLY="$TMPD/cohorts.txt"
: > "$TALLY"
for i in $(seq 1 500); do
  R=$(curl -s -X POST "$API/v1/evaluate/$FLAG_KEY" \
    -H "X-Client-API-Key: $API_KEY" -H 'content-type: application/json' \
    -d "{\"user_id\":\"user_$i\"}")
  jqr "$R" .cohort_name >> "$TALLY"
done
CTRL=$(grep -c '^control$' "$TALLY" || true)
TRT=$(grep -c '^treatment$' "$TALLY" || true)
echo "    distribution: control=$CTRL treatment=$TRT"
if [ "$CTRL" -ge 260 ] && [ "$CTRL" -le 340 ] && [ "$TRT" -ge 160 ] && [ "$TRT" -le 240 ]; then
  pass "500 evals within ±8% of 60/40 target"
else
  fail "distribution out of tolerance" "control=$CTRL treatment=$TRT"
fi
rm -rf "$TMPD"

# ---------------- 9. Stickiness ----------------
section "9. Stickiness (same params → same cohort)"
R1=$(curl -s -X POST "$API/v1/evaluate/$FLAG_KEY" -H "X-Client-API-Key: $API_KEY" \
  -H 'content-type: application/json' -d '{"user_id":"sticky"}')
R2=$(curl -s -X POST "$API/v1/evaluate/$FLAG_KEY" -H "X-Client-API-Key: $API_KEY" \
  -H 'content-type: application/json' -d '{"user_id":"sticky"}')
R3=$(curl -s -X POST "$API/v1/evaluate/$FLAG_KEY" -H "X-Client-API-Key: $API_KEY" \
  -H 'content-type: application/json' -d '{"user_id":"sticky"}')
C1=$(jqr "$R1" .cohort_name); C2=$(jqr "$R2" .cohort_name); C3=$(jqr "$R3" .cohort_name)
[ "$C1" = "$C2" ] && [ "$C2" = "$C3" ] && pass "same input → same cohort ($C1)" \
  || fail "stickiness broken" "$C1 $C2 $C3"

# ---------------- 10. Cache hit ----------------
section "10. Second identical call → reason: cached"
REASON=$(jqr "$R2" .reason)
[ "$REASON" = "cached" ] && pass "reason=cached on repeat call" \
  || fail "cache not hit" "reason=$REASON"

# ---------------- 11. Update flag + cache invalidation ----------------
section "11. Update flag (invalidates cache)"
U=$(curl -s -X PATCH "$API/api/flags/$FLAG_ID" \
  -H "authorization: Bearer $JWT" -H 'content-type: application/json' \
  -d '{"description":"updated via smoke"}')
UD=$(jqr "$U" .description)
[ "$UD" = "updated via smoke" ] && pass "PATCH flag → updated" || fail "update" "$U"
# Re-eval — should hit DB path (but still same cohort due to deterministic bucketing)
R4=$(curl -s -X POST "$API/v1/evaluate/$FLAG_KEY" -H "X-Client-API-Key: $API_KEY" \
  -H 'content-type: application/json' -d '{"user_id":"sticky"}')
R4REASON=$(jqr "$R4" .reason)
[ "$R4REASON" = "computed" ] && pass "post-edit reason=computed (cache invalidated)" \
  || fail "cache not invalidated" "reason=$R4REASON"

# ---------------- 12. Audit logs ----------------
section "12. Audit log"
sleep 2  # give celery worker a moment
A=$(curl -s "$API/api/audit/?resource_type=flag&resource_id=$FLAG_ID" -H "authorization: Bearer $JWT")
ACNT=$(jqr "$A" '.logs | length')
[ "$ACNT" -ge 1 ] && pass "audit has $ACNT entries for flag" || fail "audit empty" "$A"

# ---------------- 13. Analytics ----------------
section "13. Analytics"
sleep 2
AN=$(curl -s "$API/api/analytics/flags/$FLAG_ID" -H "authorization: Bearer $JWT")
TOTAL=$(jqr "$AN" .total_requests)
[ "$TOTAL" -ge 500 ] && pass "analytics total_requests=$TOTAL" \
  || fail "analytics not recorded" "$AN"

# ---------------- 14. Soft delete ----------------
section "14. Soft delete"
DEL=$(curl -s -o /dev/null -w '%{http_code}' -X DELETE "$API/api/flags/$FLAG_ID" \
  -H "authorization: Bearer $JWT")
[ "$DEL" = "204" ] && pass "DELETE /api/flags/$FLAG_ID → 204" || fail "delete" "got $DEL"
G=$(curl -s -o /dev/null -w '%{http_code}' "$API/api/flags/$FLAG_ID" -H "authorization: Bearer $JWT")
[ "$G" = "404" ] && pass "post-delete GET → 404" || fail "post-delete get" "got $G"

# ---------------- 15. Rotate API key ----------------
section "15. Rotate API key"
NK=$(curl -s -X POST "$API/api/clients/rotate-api-key" -H "authorization: Bearer $JWT")
NEW_KEY=$(jqr "$NK" .api_key)
[ -n "$NEW_KEY" ] && [ "$NEW_KEY" != "$API_KEY" ] && pass "rotate → new key" \
  || fail "rotate" "$NK"

# old key should be invalid — eval on any flag
# (flag is deleted so create a throwaway for this test)
THROW_KEY="throw_${EPOCH}"
curl -s -X POST "$API/api/flags/" -H "authorization: Bearer $JWT" -H 'content-type: application/json' \
  -d "{\"flag_key\":\"$THROW_KEY\",\"name\":\"t\",\"default_value\":1,\"cohorts\":[{\"id\":\"\",\"name\":\"a\",\"percentage\":100,\"value\":1}]}" > /dev/null
OLD=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/v1/evaluate/$THROW_KEY" \
  -H "X-Client-API-Key: $API_KEY" -H 'content-type: application/json' -d '{}')
[ "$OLD" = "401" ] && pass "old API key → 401" || fail "old key not invalidated" "got $OLD"
NEW=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/v1/evaluate/$THROW_KEY" \
  -H "X-Client-API-Key: $NEW_KEY" -H 'content-type: application/json' -d '{}')
[ "$NEW" = "200" ] && pass "new API key → 200" || fail "new key not working" "got $NEW"

# ---------------- Summary ----------------
printf '\n================================================\n'
printf '  Total: %s  %s pass  %s fail\n' "$((PASS+FAIL))" "$(color '32' "$PASS")" "$(color '31' "$FAIL")"
printf '================================================\n'
[ "$FAIL" -eq 0 ]
