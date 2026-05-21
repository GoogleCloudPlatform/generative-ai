# End-to-end test procedures for ADK Gemini Live API Toolkit demo app

This document provides step-by-step instructions for testing the ADK bidirectional streaming demo app using Chrome DevTools MCP server.

**Note:** All test artifacts (server logs, screenshots, test reports) are preserved in a timestamped directory for later review and analysis.

## 1. Environment setup

### Copy the demo code to a temporary directory

For testing purposes, we will copy the demo code to a timestamped temporary directory and run the demo in it.

```bash
# Create a unique timestamped directory
export TEST_DIR="/tmp/demo-$(date +%Y%m%d-%H%M%S)"
mkdir -p $TEST_DIR
cp -r src/demo/* $TEST_DIR
cd $TEST_DIR
```

### Run the demo app

- Follow the instructions in $TEST_DIR/README.md to run the app
- Monitor $TEST_DIR/app/server.log to confirm that the server is successfully started.

## 2. End-to-End UI Testing with Chrome DevTools MCP

### Step 1: Navigate to the application

```yaml
mcp__chrome-devtools__navigate_page
url: http://localhost:8000
```

**Expected:** Page loads successfully

### Step 2: Take a snapshot to verify UI

```yaml
mcp__chrome-devtools__take_snapshot
```

**Expected elements:**

- Status indicator (should show "● Disconnected")
- Messages and Events counters (should show "Messages: 0 | Events: 0")
- API Backend radio buttons (Gemini API / Vertex AI)
- Credential input fields
- Model dropdown
- WebSocket URL field (pre-filled with `ws://localhost:8000/ws`)
- SSE URL field (pre-filled with `http://localhost:8000/sse`)
- Message input field
- Connect/Disconnect buttons
- Send/Close buttons (initially disabled)
- RunConfig checkboxes
- Log area

### Step 3: Configure credentials in the UI

Use tests/e2e/.env to copy appropriate values to the UI

**For Gemini API:**

```yaml
mcp__chrome-devtools__fill
uid: <api-key-field-uid>
value: your_api_key_here
```

**For Vertex AI:**

```yaml
mcp__chrome-devtools__click
uid: <vertex-radio-button-uid>

mcp__chrome-devtools__fill
uid: <gcp-project-field-uid>
value: your_project_id

mcp__chrome-devtools__fill
uid: <gcp-location-field-uid>
value: us-central1
```

### Step 4: Connect WebSocket

```yaml
mcp__chrome-devtools__click
uid: <connect-button-uid>
```

**Expected:**

- Status changes to "● Connected (WebSocket)"
- Log shows: `[INFO] WebSocket connection established`
- Both "send_content()" and "close()" buttons become enabled

### Step 5: Send a test message

```yaml
mcp__chrome-devtools__fill
uid: <message-input-uid>
value: Hello! Can you explain what ADK streaming is?

mcp__chrome-devtools__click
uid: <send-button-uid>
```

**Expected in log:**

1. `[SENT] Hello! Can you explain what ADK streaming is?`
2. Messages counter increases to 1
3. **Tool execution events** (JSON objects):
   - `executableCode` object showing Google Search invocation with query
   - `codeExecutionResult` object with outcome "OUTCOME_OK"
4. Multiple `[PARTIAL]` events showing streaming text chunks in real-time
5. Events counter increases (typically 10-15+ events for a complete response)
6. `[COMPLETE]` event with full response
7. `[TURN COMPLETE]` event marking end of response

**Note:** Wait 2-3 seconds for the streaming response to complete before proceeding to screenshot

### Step 6: Take screenshot of results

```yaml
mcp__chrome-devtools__take_screenshot
filePath: $TEST_DIR/streaming_results.png
```

**Expected:** Screenshot showing streaming conversation with partial and complete events

Screenshot will be saved to `$TEST_DIR/streaming_results.png`

### Step 7: Test graceful close

```yaml
mcp__chrome-devtools__click
uid: <close-button-uid>
```

**Expected:**

- Log shows: `[INFO] Sending graceful close signal via WebSocket`
- Connection closes cleanly
- Note: Connection status may remain "Connected" in UI; check server logs to confirm clean closure

### Step 8: Check console for errors

```yaml
mcp__chrome-devtools__list_console_messages
```

**Expected:** No critical JavaScript errors

- Acceptable warnings: password field warnings, 404 errors for favicon
- Any errors related to application logic should be investigated

### Step 9: Check server logs for errors

```bash
cat $TEST_DIR/app/server.log | grep -i error
```

**Expected:** No output (grep returns nothing when no errors are found)

- If errors appear, review them to ensure they are non-critical (e.g., deprecation warnings)

## 3. Test Completion

### 3.1 Stop the Server

```bash
# Find and kill the server process
pkill -f "uvicorn app.main"
```

**Expected output from run.sh cleanup:**

```text
Stopping server (PID: <process-id>)...
Server stopped
```

### 3.2 Save Test Report

After completing all test steps, generate a comprehensive test report documenting the results.

The test report will be saved to: `$TEST_DIR/test_report.md`

**Test artifacts preserved** in `$TEST_DIR`:

- `app/server.log` - Server logs from the test run
- `test_report.md` - Comprehensive test report
- Screenshots (if saved to this directory)
- Any other test-related files

### 3.3 Troubleshooting

#### Server doesn't start

- Check if port 8000 is already in use: `lsof -i :8000`
- Review server.log for startup errors: `cat $TEST_DIR/app/server.log`
- Ensure virtual environment is properly set up

#### WebSocket connection fails

- Verify server is running: `curl http://localhost:8000/healthz`
- Check browser console for connection errors
- Ensure credentials are properly configured
- Review server logs: `tail -f $TEST_DIR/app/server.log`

#### No streaming events appear

- Verify API key is valid
- Check server.log for API errors: `cat $TEST_DIR/app/server.log | grep -i error`
- Ensure the model selected supports Live API (models with "live" in the name)

#### Browser page closed unexpectedly

- Use `mcp__chrome-devtools__new_page` to open a new page
- Navigate to `http://localhost:8000` again
- Continue testing from the appropriate step

## 4. Test Report

Generate a comprehensive test report and save it to `$TEST_DIR/test_report.md`.

The test report should include:

- **Test Summary**: Overall status (PASSED/FAILED), date, duration
- **Environment Details**: Test directory location, server configuration
- **Step-by-step Results**: Each test step with actual vs expected outcomes
- **Streaming Metrics**: Messages sent, events received, tool invocations
- **Error Analysis**: Console errors, server log errors (if any)
- **Screenshots**: Reference to captured screenshots
- **Observations**: Notable behaviors, tool executions, streaming performance
- **Conclusion**: Overall assessment and any issues found

**Test Artifacts Location**: All test artifacts (server logs, screenshots, test report) are preserved in `$TEST_DIR` for future reference.

**Example command to view test results:**

```bash
echo "Test directory: $TEST_DIR"
ls -lh $TEST_DIR/test_report.md
cat $TEST_DIR/test_report.md
```
