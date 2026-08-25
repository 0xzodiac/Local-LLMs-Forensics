# LM Studio Stateful API Logging Assessment

## Discovered Endpoints

| Endpoint | Method | Type | Status |
|---|---|---|---|
| `/v1/models` | GET | OpenAI | Responded |
| `/v1/chat/completions` | POST | OpenAI | Functional |
| `/v1/completions` | POST | OpenAI | Documented |
| `/v1/embeddings` | POST | OpenAI | Documented |
| `/v1/responses` | POST | OpenAI (Responses API) | Responded (empty) |
| `/api/v1/models` | GET | LM Studio native | Functional |
| `/api/v1/chat` | POST | LM Studio native | Requires `input` field |
| `/api/v1/models/load` | POST | LM Studio native | Documented |
| `/api/v1/models/download` | POST | LM Studio native | Documented |
| `/v1/chat/history` | GET | Custom | 404 |
| `/conversations` | GET | Custom | 404 |

## Logging Artifacts Discovered

### 1. Server Logs: `~/.lmstudio/server-logs/YYYY-MM/YYYY-MM-DD.N.log`
- **Full HTTP request bodies logged at DEBUG level**, including all message content
- Captures both OpenAI-compatible and LM Studio native API calls
- Logs persist indefinitely - log files can reach multi-MB size
- **Canaries confirmed present** in server logs for both stateless and stateful calls:
  - `STATELESS_BASELINE_1781929025` logged with full body
  - `STATEFUL_CALL_1781972228` logged with full body
- File rotated daily (.1, .2, etc.)

### 2. Prediction History: `~/.lmstudio/.internal/api-prediction-history/packs/pack-NNNN.json`
- Sharded storage of API call inputs/outputs with full message content
- Only 2 nodes captured (from Qwen3.5-9B testing via `/api/v1/chat` and `/v1/chat/completions`)
- Contains `modelKey`, `input.messages[].content[].text`, `output`, timestamps
- **Not all API calls are captured** - selection criteria unclear (may require LM Studio native API or specific model)
- Index file at `api-prediction-history/index.json` maps node IDs to packs

### 3. Server Logs State: `~/.lmstudio/.internal/server-logs-state.json`
- Tracks current log file path and size
- Rotates when file grows large or server restarts

### 4. Conversations Directory: `~/.lmstudio/conversations/`
- Empty. No conversation persistence.

### 5. Dev Logs: `~/.lmstudio/dev-logs/dev-logs-state.json`
- Minimal state file (`lastWrittenFile: null`). No historical data.

### 6. Other Internal State Files (`~/.lmstudio/.internal/`)
- `http-server-config.json` - server binding config
- `backend-preferences-v1.json` - backend settings
- `internal-engine-index.json` - engine registry
- No sensitive payload leakage found in these

## Comparison: Stateless vs Stateful Logging

| Aspect | Stateless (`/v1/chat/completions`) | Stateful (`/api/v1/chat`) | Notes |
|---|---|---|---|
| **Server log capture** | Full request body logged | Full request body logged | Identical behavior |
| **Prediction history** | Selective (captured Qwen, not Nemotron) | Selective (captured Qwen, not Nemotron) | Selection criteria unknown |
| **Conversation persistence** | None | None | No differences |
| **Response logging** | Full response in logs | Full response in logs | Identical |
| **Disk artifact creation** | Server logs + maybe prediction history | Server logs + maybe prediction history | No meaningful difference |

## Residual Risk Assessment

| Risk | Severity | Details |
|---|---|---|
| **Server log data persistence** | **HIGH** | Server logs at `~/.lmstudio/server-logs/` capture ALL API request bodies in plaintext. No TTL/retention limit observed. Logs persist until manually deleted. |
| **Prediction history spillage** | **MEDIUM** | `api-prediction-history/packs/` stores message content with timestamps and model keys. Selection logic is opaque; some calls are captured, others are not. |
| **No per-request opt-out** | **HIGH** | No header/parameter to prevent request logging. All API calls are logged regardless of sensitivity. |
| **Multi-tenant / shared system risk** | **HIGH** | Data written to user-writable directory. Any process with filesystem access to `~/.lmstudio/` can read historical API traffic. |
| **Log rotation gap** | **MEDIUM** | When server restarts, new log file starts but previous files are never cleaned up. `2026-06-19.1.log` is 6.3 MB for a single day. |

## Key Finding
LM Studio does not offer a true "stateful" vs "stateless" distinction at the API level. Both `/v1/chat/completions` (OpenAI-compatible) and `/api/v1/chat` (native) produce identical logging behavior. The **server logs** are the primary persistence risk, not the prediction history packs. The prediction history pack appears to selectively capture data for specific models/endpoints, not for all API traffic.
