# Tutorial: Run the Contract Compliance Multi-Agent Demo

This tutorial walks through the executable demo in this repository. A Python FastAPI service handles contract intake, deterministic extraction, ADK `RemoteA2aAgent` handoff, case state, and artifacts. A Go A2A service enforces deterministic compliance rules and returns a JSON-RPC `SendMessage` task verdict.

The live cockpit path does not require a Gemini API key.

## 1. Start the Services

Start the Go compliance agent:

```bash
cd go-compliance-agent
go run cmd/server/main.go
```

The Go service exposes:

```text
http://localhost:8888/.well-known/agent.json
http://localhost:8888/
```

Start the Python cockpit:

```bash
cd python-extraction-agent
uv sync
uv run uvicorn app.fast_api_app:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/live-compliance/
```

## 2. Run the Happy Path

1. Select `standard-vendor-agreement.pdf`.
2. Keep **A2A Simulator Mode** on `Healthy`.
3. Click **Run Pipeline Audit**.
4. Confirm the Agent Exchange panel shows:
   - source: `python-extraction-agent`
   - target: `Security Compliance Validator`
   - method: `SendMessage`
   - a task ID
   - a JSON-RPC payload
   - a passed Go verdict
5. Open the generated compliance certificate artifact.

Expected result: the contract passes because value, term, insurance, liability, renewal, and exit terms are within policy.

## 3. Run the Review Paths

Test the bundled failure cases:

| Contract | Expected Result |
|:---|:---|
| `high-risk-liability-contract.pdf` | Review because unlimited liability is prohibited. |
| `non-compliant-contract.pdf` | Review with multiple policy violations. |

For `non-compliant-contract.pdf`, the UI should show review required with these violation categories:

- value above `$500k`
- unlimited liability
- auto-renewal longer than 3 years
- insurance below `$1M`
- term longer than 5 years
- missing usable exit clause

## 4. Simulate A2A Failure

Use **A2A Simulator Mode** to test remote-agent failure behavior:

- `Healthy`: normal Go service path.
- `Delayed`: waits before the Go call, bounded by the backend.
- `Crashed (503)`: simulates Go service failure and routes to manual review.

Expected crashed result: Python fails closed to `MANUAL_REVIEW` and the certificate explains that manual legal review is required.

## 5. What the Browser Sends

The UI posts contract text and policy settings to:

```text
POST /api/compliance/upload
```

Important form fields:

| Field | Purpose |
|:---|:---|
| `file` | Text contract fixture, including `.pdf`-named text samples. |
| `custom_policies` | Active policy values sent to Go. |
| `simulated_latency` | Bounded delay for simulator testing. |
| `simulated_server_state` | `normal` or `crashed`. |

The browser does not call the Go service directly.

## 6. What Python Sends to Go

`python-extraction-agent/app/fast_api_app.py` builds the A2A request in `build_go_message_payload(...)`.

The live method is:

```text
SendMessage
```

The payload contains:

- `jsonrpc: "2.0"`
- `task_id`
- extracted contract fields
- active policy settings

ADK sends the request through `RemoteA2aAgent`; it is not a manual browser-to-Go call.

## 7. What Go Validates

`go-compliance-agent/internal/compliance/checker.go` checks:

- contract value <= `max_contract_value`
- insurance coverage >= `required_insurance_minimum`
- term length <= `max_term_years`
- termination clause present when required
- no prohibited unlimited liability clause
- no prohibited auto-renewal longer than 3 years

Default thresholds live in:

```text
go-compliance-agent/internal/policies/default_policy.json
```

## 8. Key Code To Read

| File | Why it matters |
|:---|:---|
| `python-extraction-agent/app/fast_api_app.py` | API routes, request validation, ADK handoff, simulator handling. |
| `python-extraction-agent/app/tools.py` | Deterministic contract extraction and risk classification. |
| `python-extraction-agent/app/live_compliance.py` | Case state and generated HTML artifacts. |
| `python-extraction-agent/app/static/live-compliance/index.html` | Live cockpit UI and A2A payload display. |
| `go-compliance-agent/internal/agentcard/card.go` | Agent Card discovery response. |
| `go-compliance-agent/internal/handler/task_handler.go` | JSON-RPC `SendMessage` and legacy task handlers. |
| `go-compliance-agent/internal/compliance/checker.go` | Deterministic policy verdict. |

## 9. Test the Demo

Run Python tests:

```bash
cd python-extraction-agent
uv run pytest tests/unit -v
```

Run Go tests:

```bash
cd go-compliance-agent
go test -v ./...
```

Smoke-test the Agent Card:

```bash
curl http://127.0.0.1:8888/.well-known/agent.json
```

From the repository root, smoke-test a non-compliant upload:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/compliance/upload \
  -F file=@sample-contracts/non-compliant-contract.pdf \
  -F simulated_latency=0 \
  -F simulated_server_state=normal \
  -F 'custom_policies={"max_contract_value":500000,"required_insurance_minimum":1000000,"max_term_years":5,"required_termination_clause":true,"prohibited_clauses":["unlimited liability","auto-renewal > 3yr"]}'
```

Expected result: response JSON contains `passed: false` and a list of Go policy violations.
