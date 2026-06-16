package handler

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHandleJSONRPCMessageSend(t *testing.T) {
	InitPolicies("../policies/default_policy.json")
	resetStoredTasks()

	payload := map[string]interface{}{
		"jsonrpc": "2.0",
		"id":      "rpc-1",
		"method":  "SendMessage",
		"params": map[string]interface{}{
			"metadata": map[string]interface{}{"task_id": "case-123"},
			"message": map[string]interface{}{
				"kind":      "message",
				"messageId": "msg-1",
				"role":      "ROLE_USER",
				"parts": []map[string]interface{}{
					{
						"data": map[string]interface{}{
							"schema_version": "contract-compliance.a2a.v1",
							"case_id":        "case-123",
							"contract": map[string]interface{}{
								"contract_value":         250000.0,
								"contractor_name":        "ACME CLOUD SOLUTIONS",
								"client_name":            "GFD PLATFORM SYSTEMS",
								"start_date":             "2026-06-01",
								"end_date":               "2028-06-01",
								"liability_limit":        "$1,000,000",
								"insurance_coverage":     2000000.0,
								"auto_renewal":           false,
								"has_termination_clause": true,
								"term_length_years":      2,
							},
						},
						"mediaType": "application/json",
					},
				},
			},
		},
	}

	response := postJSONRPC(t, payload)

	if response.Error != nil {
		t.Fatalf("unexpected JSON-RPC error: %+v", response.Error)
	}
	if response.Result.Kind != "task" {
		t.Fatalf("expected A2A task result, got %q", response.Result.Kind)
	}
	if response.Result.ID != "case-123" {
		t.Fatalf("expected task id case-123, got %q", response.Result.ID)
	}
	if response.Result.Status.State != "TASK_STATE_COMPLETED" {
		t.Fatalf("expected completed task state TASK_STATE_COMPLETED, got %q", response.Result.Status.State)
	}

	message := response.Result.Status.Message
	if message == nil {
		t.Fatal("expected status message")
	}
	if message.Role != "ROLE_AGENT" {
		t.Fatalf("expected message role ROLE_AGENT, got %q", message.Role)
	}
	if len(message.Parts) != 1 || message.Parts[0].MediaType != "application/json" {
		t.Fatalf("expected one A2A data part with mediaType application/json, got %+v", message.Parts)
	}
	if passed, ok := message.Parts[0].Data["passed"].(bool); !ok || !passed {
		t.Fatalf("expected passed verdict, got %+v", message.Parts[0].Data["passed"])
	}
}

func TestHandleJSONRPCLegacyTasksSendStillWorks(t *testing.T) {
	InitPolicies("../policies/default_policy.json")
	resetStoredTasks()

	payload := map[string]interface{}{
		"jsonrpc": "2.0",
		"id":      "rpc-legacy",
		"method":  "tasks/send",
		"params": map[string]interface{}{
			"id": "legacy-task",
			"message": map[string]interface{}{
				"role": "user",
				"parts": []map[string]interface{}{
					{
						"type": "data",
						"data": map[string]interface{}{
							"contract_value":         900000.0,
							"contractor_name":        "Risky Vendor",
							"client_name":            "GFD PLATFORM SYSTEMS",
							"start_date":             "2026-06-01",
							"end_date":               "2032-06-01",
							"liability_limit":        "unlimited liability",
							"insurance_coverage":     500000.0,
							"auto_renewal":           true,
							"has_termination_clause": false,
							"term_length_years":      6,
						},
					},
				},
			},
		},
	}

	response := postJSONRPC(t, payload)

	if response.Error != nil {
		t.Fatalf("unexpected JSON-RPC error: %+v", response.Error)
	}
	if response.Result.ID != "legacy-task" {
		t.Fatalf("expected legacy task id, got %q", response.Result.ID)
	}

	parts := response.Result.Status.Message.Parts
	if len(parts) != 1 || parts[0].Type != "data" {
		t.Fatalf("expected legacy type=data response part, got %+v", parts)
	}
	if passed, ok := parts[0].Data["passed"].(bool); !ok || passed {
		t.Fatalf("expected failing verdict, got %+v", parts[0].Data["passed"])
	}
}

func postJSONRPC(t *testing.T, payload map[string]interface{}) struct {
	JSONRPC string        `json:"jsonrpc"`
	ID      string        `json:"id"`
	Result  Task          `json:"result"`
	Error   *JSONRPCError `json:"error"`
} {
	t.Helper()

	body, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("marshal payload: %v", err)
	}

	request := httptest.NewRequest(http.MethodPost, "/", bytes.NewReader(body))
	recorder := httptest.NewRecorder()
	HandleJSONRPC(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("expected HTTP 200, got %d", recorder.Code)
	}

	var response struct {
		JSONRPC string        `json:"jsonrpc"`
		ID      string        `json:"id"`
		Result  Task          `json:"result"`
		Error   *JSONRPCError `json:"error"`
	}
	if err := json.Unmarshal(recorder.Body.Bytes(), &response); err != nil {
		t.Fatalf("unmarshal response: %v", err)
	}
	return response
}

func resetStoredTasks() {
	tasksMu.Lock()
	defer tasksMu.Unlock()
	tasks = make(map[string]*Task)
}
