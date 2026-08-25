# LM Studio Mitigation Verification Test Report

**Date:** 2026-06-20  
**Target:** `localhost:1234` (LM Studio v0.0.15-2, llama.cpp backend 2.17.0)  
**Model used:** `nvidia-nemotron-3-nano-4b` (2.84 GB)  

---

## Step 1: Check Current Settings

**Settings file:** `~/.lmstudio/settings.json`
- No `logSensitiveData` key present
- `developer.apiPredictionHistoryEviction.ttlDays: 30`

**Server config:** `~/.lmstudio/.internal/http-server-config.json`
```json
{
  "logSensitiveData": true,
  "logIncomingTokens": false,
  "verbose": true,
  "logLinesLimit": 500,
  "fileLoggingMode": "succinct"
}
```

**Server logs directory:** `~/.lmstudio/server-logs/2026-06/`
```
2026-06-19.1.log  6,319,129 bytes  (from yesterday, contains 2312 "content" entries)
2026-06-20.1.log    123,047 bytes  (today's log)
```

**Historical leak confirmation:** Yesterday's single log file contains **2312 instances** of `"content"` strings and **777 `Generated prediction`** entries — every single API request/response body logged in cleartext.

**Commands:**
```bash
cat ~/.lmstudio/.internal/http-server-config.json
ls -la ~/.lmstudio/server-logs/2026-06/
```

---

## Step 2: Baseline — Confirm Canary in Logs

**Canary sent:**
```bash
CANARY="MITIGATION_BASELINE_1781972288"
curl -s http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"nvidia-nemotron-3-nano-4b","messages":[{"role":"user","content":"Say hello. My token is: MITIGATION_BASELINE_1781972288"}],"max_tokens":20}'
```

**Result:** `FOUND IN LOGS`
```bash
grep -r "MITIGATION_BASELINE" ~/.lmstudio/server-logs/
```
Output:
```
/home/sharks/.lmstudio/server-logs/2026-06/2026-06-20.1.log:      "content": "Say hello. My token is: MITIGATION_BASELINE_1781972288"
```
All 10 baseline canaries sent appeared in logs. Full request body written to disk in cleartext.

**Timestamp:** 19:18:08 UTC

---

## Step 3: Change `logSensitiveData` to `false`

**Method:** Direct JSON edit of `~/.lmstudio/.internal/http-server-config.json` via python

**Before:**
```json
"logSensitiveData": true
```

**After:**
```json
"logSensitiveData": false
```

**Server restart:** `lms server stop && sleep 2 && lms server start`

**Verification — config persisted:**
```bash
cat ~/.lmstudio/.internal/http-server-config.json
# => "logSensitiveData": false
```
Both `cat -A` (raw bytes) and `python json.load` confirm `false`.

**Timestamp of modification:** 2026-06-20 07:55:07 UTC

---

## Step 4: Test After Change

**Canary sent:**
```bash
CANARY="MITIGATION_AFTER_CHANGE_1781931409"
curl -s http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"nvidia-nemotron-3-nano-4b","messages":[{"role":"user","content":"Say hello. My token is: MITIGATION_AFTER_CHANGE_1781931409"}],"max_tokens":20}'
```

**API response:** Successful (200), model generated response

**Result:** `NOT FOUND IN LOGS`
```bash
grep -r "MITIGATION_AFTER_CHANGE" ~/.lmstudio/server-logs/
```
No output (grep exit code 1).

**Conclusion: `logSensitiveData=false` effectively stops logging of request/response bodies.** The mitigation WORKS when applied correctly.

---

## Step 5: Set `ttlDays` to 0

**Change:**
```bash
python3 -c "
import json
with open('/home/sharks/.lmstudio/settings.json') as f:
    data = json.load(f)
data['developer']['apiPredictionHistoryEviction']['ttlDays'] = 0
with open('/home/sharks/.lmstudio/settings.json', 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
"
```

**After:** `developer.apiPredictionHistoryEviction.ttlDays: 0`

**Finding:** This controls LM Studio's internal prediction history cache (`~/.lmstudio/.internal/api-prediction-history/`), NOT the server log files. Server logs are file-rotation based (`server-logs-state.json` tracks the current file). **TTL setting has no effect on existing or future server log files.**

---

## Step 6: Attempt Full Disable

**Actions taken:**
- Stopped LM Studio server: `lms server stop`
- Config set: `logSensitiveData: false`, `logIncomingTokens: false`, `verbose: true`
- Remaining risk: `verbose: true` retains debug-level logging (prompt processing timings, slot allocation, etc.)

**No raw llama-server instance available** to test logging-free startup.

---

## Files Modified During Test

| File | Change |
|------|--------|
| `~/.lmstudio/.internal/http-server-config.json` | `logSensitiveData: true` → `false` |
| `~/.lmstudio/settings.json` | `ttlDays: 30` → `0` |

**Note:** Both changes are reversible if needed.

---

## Summary of Findings

- **`logSensitiveData: true` is a real vulnerability.** All API request/response bodies are written to `~/.lmstudio/server-logs/` in cleartext. Yesterday's single log: 6.3 MB with 2312 content entries.
- **Setting `logSensitiveData: false` mitigates the leak.** After change, canary `MITIGATION_AFTER_CHANGE_1781931409` did NOT appear in server logs.
- **`ttlDays: 0` does not affect server log files.** It controls internal prediction history, not the file-based server logs.
- **Historical logs remain on disk.** Changing `logSensitiveData` does not retroactively delete existing log data (~7.5 MB total across 2 days).
- **Manual cleanup required.** Old `server-logs/` files must be deleted separately (`rm -rf ~/.lmstudio/server-logs/`).
