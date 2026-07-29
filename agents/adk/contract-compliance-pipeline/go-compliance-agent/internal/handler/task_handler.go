package handler

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"sync"
	"time"

	"go-compliance-agent/internal/compliance"
)

// --- JSON-RPC 2.0 request/response structures per A2A protocol specification ---

// JSONRPCRequest is the standard JSON-RPC 2.0 request envelope.
// The A2A protocol uses JSON-RPC as its wire format for all agent communication.
type JSONRPCRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      interface{}     `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}

// JSONRPCResponse is the standard JSON-RPC 2.0 response envelope.
type JSONRPCResponse struct {
	JSONRPC string        `json:"jsonrpc"`
	ID      interface{}   `json:"id"`
	Result  interface{}   `json:"result,omitempty"`
	Error   *JSONRPCError `json:"error,omitempty"`
}

// JSONRPCError carries error details inside a JSON-RPC response.
type JSONRPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// --- A2A Task, Message, and Part structures ---

// MessageSendParams contains the parameters for the current A2A message/send method.
type MessageSendParams struct {
	Message  Message                `json:"message"`
	Metadata map[string]interface{} `json:"metadata,omitempty"`
}

// TaskSendParams contains the parameters for the legacy tasks/send JSON-RPC method.
type TaskSendParams struct {
	ID      string  `json:"id"`
	Message Message `json:"message"`
}

// TaskGetParams contains the parameters for the tasks/get JSON-RPC method.
type TaskGetParams struct {
	ID string `json:"id"`
}

// Task represents an A2A task with its current status and any produced artifacts.
type Task struct {
	ContextID    string                 `json:"contextId"`
	ID           string                 `json:"id"`
	Kind         string                 `json:"kind,omitempty"`
	Metadata     map[string]interface{} `json:"metadata,omitempty"`
	Status       TaskStatus             `json:"status"`
	Artifacts    []Artifact             `json:"artifacts,omitempty"`
	CreatedAt    string                 `json:"createdAt,omitempty"`
	LastModified string                 `json:"lastModified,omitempty"`
}

// TaskStatus tracks the lifecycle state of a task.
type TaskStatus struct {
	State   string   `json:"state"`
	Message *Message `json:"message,omitempty"`
}

// Message represents a conversational turn between user and agent, containing typed Parts.
type Message struct {
	ContextID string                 `json:"contextId,omitempty"`
	Kind      string                 `json:"kind,omitempty"`
	MessageID string                 `json:"messageId,omitempty"`
	Metadata  map[string]interface{} `json:"metadata,omitempty"`
	Role      string                 `json:"role"`
	TaskID    string                 `json:"taskId,omitempty"`
	Parts     []Part                 `json:"parts"`
}

// Part is a polymorphic content unit — either text, raw bytes, URL, or structured data.
type Part struct {
	Kind      string                 `json:"kind,omitempty"`      // legacy v0.3
	Type      string                 `json:"type,omitempty"`      // legacy v0.3
	Text      string                 `json:"text,omitempty"`      // v1.0 & v0.3
	URL       string                 `json:"url,omitempty"`       // v1.0
	Filename  string                 `json:"filename,omitempty"`  // v1.0
	MediaType string                 `json:"mediaType,omitempty"` // v1.0
	Raw       string                 `json:"raw,omitempty"`       // v1.0
	Data      map[string]interface{} `json:"data,omitempty"`      // v1.0 & v0.3
}

// Artifact is a named output produced by the agent during task execution.
type Artifact struct {
	Name  string `json:"name,omitempty"`
	Parts []Part `json:"parts"`
}

var (
	tasksMu sync.RWMutex
	tasks   = make(map[string]*Task)
	policy  compliance.Policy
)

// InitPolicies configures the checker thresholds from targeted config paths.
func InitPolicies(policyPath string) {
	loadedPolicy, err := compliance.LoadPolicy(policyPath)
	if err != nil {
		fmt.Printf("Warning: Failed to load policy file at %s: %v. Bootstrapping defaults.\n", policyPath, err)
		policy = compliance.Policy{
			MaxContractValue:          500000.0,
			ProhibitedClauses:         []string{"unlimited liability", "auto-renewal > 3yr"},
			RequiredInsuranceMinimum:  1000000.0,
			MaxTermYears:              5,
			RequiredTerminationClause: true,
		}
		return
	}
	policy = loadedPolicy
}

// HandleJSONRPC is the single entry point for all A2A JSON-RPC 2.0 requests.
// The A2A protocol routes all operations through JSON-RPC method dispatch
// rather than separate REST endpoints.
func HandleJSONRPC(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	if r.Method != http.MethodPost {
		writeJSONRPCError(w, nil, -32600, "Only POST method is accepted")
		return
	}

	// Decode the JSON-RPC envelope
	var req JSONRPCRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSONRPCError(w, nil, -32700, "Parse error: invalid JSON")
		return
	}

	// Validate JSON-RPC version
	if req.JSONRPC != "2.0" {
		writeJSONRPCError(w, req.ID, -32600, "Invalid request: jsonrpc must be '2.0'")
		return
	}

	// Dispatch to the appropriate handler based on the A2A method name
	switch req.Method {
	case "message/send", "SendMessage":
		result, rpcErr := handleMessageSend(req.Params)
		if rpcErr != nil {
			writeJSONRPCError(w, req.ID, rpcErr.Code, rpcErr.Message)
			return
		}
		writeJSONRPCResult(w, req.ID, result)

	case "tasks/send":
		result, rpcErr := handleTasksSend(req.Params)
		if rpcErr != nil {
			writeJSONRPCError(w, req.ID, rpcErr.Code, rpcErr.Message)
			return
		}
		writeJSONRPCResult(w, req.ID, result)

	case "tasks/get", "GetTask":
		result, rpcErr := handleTasksGet(req.Params)
		if rpcErr != nil {
			writeJSONRPCError(w, req.ID, rpcErr.Code, rpcErr.Message)
			return
		}
		writeJSONRPCResult(w, req.ID, result)

	default:
		writeJSONRPCError(w, req.ID, -32601, fmt.Sprintf("Method not found: %s", req.Method))
	}
}

// handleMessageSend processes the current A2A message/send request shape.
// It accepts a Message containing a structured DataPart and returns a completed Task.
func handleMessageSend(params json.RawMessage) (*Task, *JSONRPCError) {
	var sendParams MessageSendParams
	if err := json.Unmarshal(params, &sendParams); err != nil {
		return nil, &JSONRPCError{Code: -32602, Message: "Invalid params: " + err.Error()}
	}

	taskID := sendParams.Message.TaskID
	if taskID == "" {
		taskID = stringValue(sendParams.Metadata, "task_id")
	}

	return validateMessage(taskID, sendParams.Message, false)
}

// handleTasksSend processes the legacy A2A tasks/send request shape.
// It is retained for older clients; the live demo uses message/send.
func handleTasksSend(params json.RawMessage) (*Task, *JSONRPCError) {
	var sendParams TaskSendParams
	if err := json.Unmarshal(params, &sendParams); err != nil {
		return nil, &JSONRPCError{Code: -32602, Message: "Invalid params: " + err.Error()}
	}

	if sendParams.ID == "" {
		return nil, &JSONRPCError{Code: -32602, Message: "Missing required task id"}
	}

	return validateMessage(sendParams.ID, sendParams.Message, true)
}

func validateMessage(taskID string, message Message, includeLegacyType bool) (*Task, *JSONRPCError) {
	contractPayload, rpcErr := extractContractPayload(message)
	if rpcErr != nil {
		return nil, rpcErr
	}

	if taskID == "" {
		taskID = stringValue(contractPayload, "case_id")
	}
	if taskID == "" {
		taskID = fmt.Sprintf("task-%d", time.Now().UnixNano())
	}

	contextID := message.ContextID
	if contextID == "" {
		contextID = taskID
	}

	detailsPayload, effectivePolicy, rpcErr := unpackContractPayload(contractPayload)
	if rpcErr != nil {
		return nil, rpcErr
	}

	details, rpcErr := decodeContractDetails(detailsPayload)
	if rpcErr != nil {
		return nil, rpcErr
	}

	// Run compliance checks synchronously — pure computation, no I/O wait needed.
	result := compliance.CheckCompliance(details, effectivePolicy)
	resultMap := complianceResultMap(result)

	task := completedTask(taskID, contextID, resultMap, includeLegacyType)

	// Store the task for later retrieval via tasks/get.
	tasksMu.Lock()
	tasks[taskID] = task
	tasksMu.Unlock()

	return task, nil
}

func extractContractPayload(message Message) (map[string]interface{}, *JSONRPCError) {
	for _, part := range message.Parts {
		if (part.Kind == "data" || part.Type == "data") && part.Data != nil {
			return part.Data, nil
		}
		if part.Kind == "text" && part.Text != "" {
			var data map[string]interface{}
			if err := json.Unmarshal([]byte(part.Text), &data); err == nil {
				return data, nil
			}
		}
	}
	return nil, &JSONRPCError{Code: -32602, Message: "No data part found in message"}
}

func unpackContractPayload(payload map[string]interface{}) (map[string]interface{}, compliance.Policy, *JSONRPCError) {
	effectivePolicy := policy

	if policyData, ok := payload["policy"]; ok {
		parsedPolicy, rpcErr := decodePolicy(policyData)
		if rpcErr != nil {
			return nil, effectivePolicy, rpcErr
		}
		effectivePolicy = parsedPolicy
	}

	if nested, ok := mapValue(payload, "contract"); ok {
		return nested, effectivePolicy, nil
	}
	if nested, ok := mapValue(payload, "contract_details"); ok {
		return nested, effectivePolicy, nil
	}

	// Legacy clients send the contract fields directly in the DataPart.
	direct := make(map[string]interface{}, len(payload))
	for key, value := range payload {
		if key == "policy" || key == "risk_assessment" || key == "schema_version" || key == "case_id" {
			continue
		}
		direct[key] = value
	}
	return direct, effectivePolicy, nil
}

func decodePolicy(policyData interface{}) (compliance.Policy, *JSONRPCError) {
	policyBytes, err := json.Marshal(policyData)
	if err != nil {
		return compliance.Policy{}, &JSONRPCError{Code: -32602, Message: "Invalid policy override"}
	}

	var override compliance.Policy
	if err := json.Unmarshal(policyBytes, &override); err != nil {
		return compliance.Policy{}, &JSONRPCError{Code: -32602, Message: "Invalid policy override format: " + err.Error()}
	}
	return override, nil
}

func decodeContractDetails(contractData map[string]interface{}) (compliance.ContractDetails, *JSONRPCError) {
	if contractData == nil {
		return compliance.ContractDetails{}, &JSONRPCError{Code: -32602, Message: "No data part found in message"}
	}

	dataBytes, err := json.Marshal(contractData)
	if err != nil {
		return compliance.ContractDetails{}, &JSONRPCError{Code: -32603, Message: "Failed to marshal contract data"}
	}

	var details compliance.ContractDetails
	if err := json.Unmarshal(dataBytes, &details); err != nil {
		return compliance.ContractDetails{}, &JSONRPCError{Code: -32602, Message: "Invalid contract data format: " + err.Error()}
	}
	return details, nil
}

func complianceResultMap(result compliance.ComplianceResult) map[string]interface{} {
	resultBytes, _ := json.Marshal(result)
	var resultMap map[string]interface{}
	_ = json.Unmarshal(resultBytes, &resultMap)
	return resultMap
}

func completedTask(taskID string, contextID string, resultMap map[string]interface{}, includeLegacyType bool) *Task {
	resultPart := Part{
		Data:      resultMap,
		MediaType: "application/json",
	}
	if includeLegacyType {
		resultPart.Kind = "data"
		resultPart.Type = "data"
	}

	agentMessage := Message{
		ContextID: contextID,
		Kind:      "message",
		MessageID: fmt.Sprintf("msg-%s", taskID),
		Role:      "ROLE_AGENT", // "agent" -> "ROLE_AGENT"
		TaskID:    taskID,
		Parts:     []Part{resultPart},
	}

	now := time.Now().Format("2006-01-02T15:04:05.000Z")
	return &Task{
		ContextID: contextID,
		ID:        taskID,
		Kind:      "task",
		Status: TaskStatus{
			State:   "TASK_STATE_COMPLETED", // "completed" -> "TASK_STATE_COMPLETED"
			Message: &agentMessage,
		},
		CreatedAt:    now,
		LastModified: now,
	}
}

func mapValue(data map[string]interface{}, key string) (map[string]interface{}, bool) {
	value, ok := data[key]
	if !ok {
		return nil, false
	}
	typed, ok := value.(map[string]interface{})
	return typed, ok
}

func stringValue(data map[string]interface{}, key string) string {
	if data == nil {
		return ""
	}
	value, ok := data[key]
	if !ok {
		return ""
	}
	typed, ok := value.(string)
	if !ok {
		return ""
	}
	return typed
}

// handleTasksGet retrieves a previously submitted task by ID.
func handleTasksGet(params json.RawMessage) (*Task, *JSONRPCError) {
	var getParams TaskGetParams
	if err := json.Unmarshal(params, &getParams); err != nil {
		return nil, &JSONRPCError{Code: -32602, Message: "Invalid params: " + err.Error()}
	}

	tasksMu.RLock()
	task, exists := tasks[getParams.ID]
	tasksMu.RUnlock()

	if !exists {
		return nil, &JSONRPCError{Code: -32602, Message: "Task not found: " + getParams.ID}
	}

	return task, nil
}

// writeJSONRPCResult sends a successful JSON-RPC 2.0 response.
func writeJSONRPCResult(w http.ResponseWriter, id interface{}, result interface{}) {
	resp := JSONRPCResponse{
		JSONRPC: "2.0",
		ID:      id,
		Result:  result,
	}
	_ = json.NewEncoder(w).Encode(resp)
}

// writeJSONRPCError sends a JSON-RPC 2.0 error response.
func writeJSONRPCError(w http.ResponseWriter, id interface{}, code int, message string) {
	resp := JSONRPCResponse{
		JSONRPC: "2.0",
		ID:      id,
		Error:   &JSONRPCError{Code: code, Message: message},
	}
	_ = json.NewEncoder(w).Encode(resp)
}

// dispatchWebhook sends an A2A-formatted callback notification to the orchestrator.
func dispatchWebhook(url, taskID string, result compliance.ComplianceResult) {
	// Convert result to a generic map for the A2A DataPart
	resultBytes, _ := json.Marshal(result)
	var resultMap map[string]interface{}
	_ = json.Unmarshal(resultBytes, &resultMap)

	// Build an A2A-formatted webhook payload
	payload := map[string]interface{}{
		"jsonrpc": "2.0",
		"method":  "tasks/pushNotification",
		"params": map[string]interface{}{
			"id": taskID,
			"status": map[string]interface{}{
				"state": "completed",
				"message": map[string]interface{}{
					"role": "agent",
					"parts": []map[string]interface{}{
						{"type": "data", "data": resultMap},
					},
				},
			},
		},
	}
	bytesPayload, _ := json.Marshal(payload)

	fmt.Printf("A2A Webhook Dispatcher: Hitting callback endpoint %s\n", url)
	req, err := http.NewRequest(http.MethodPost, url, bytes.NewBuffer(bytesPayload))
	if err != nil {
		return
	}
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		fmt.Printf("A2A Webhook Trigger Error: Connection failed: %v\n", err)
		return
	}
	_ = resp.Body.Close()
	fmt.Printf("A2A Webhook Trigger Callback: Received code %d from backend listener.\n", resp.StatusCode)
}
