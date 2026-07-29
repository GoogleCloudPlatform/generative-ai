package agentcard

import (
	"encoding/json"
	"net/http"
	"os"
)

// AgentCard describes the agent's capabilities following the A2A protocol specification.
// Served at /.well-known/agent.json for discovery by other agents.
type AgentCard struct {
	Name               string             `json:"name"`
	Description        string             `json:"description"`
	Version            string             `json:"version"`
	SupportedInterfaces []AgentInterface  `json:"supportedInterfaces"`
	Capabilities       Capabilities       `json:"capabilities"`
	DefaultInputModes  []string           `json:"defaultInputModes"`
	DefaultOutputModes []string           `json:"defaultOutputModes"`
	Skills             []Skill            `json:"skills"`
}

// AgentInterface specifies a transport mechanism and protocol version for agent communication.
type AgentInterface struct {
	URL             string `json:"url"`
	ProtocolBinding string `json:"protocolBinding"`
	ProtocolVersion string `json:"protocolVersion"`
}

// Capabilities declares which optional A2A features the agent supports.
type Capabilities struct {
	ExtendedAgentCard bool `json:"extendedAgentCard"`
}

// Skill describes a specific capability the agent can perform.
type Skill struct {
	ID          string   `json:"id"`
	Name        string   `json:"name"`
	Description string   `json:"description"`
	Tags        []string `json:"tags"`
	Examples    []string `json:"examples"`
}

// GetCard returns the preloaded Go Compliance service Agent Card configuration structure.
func GetCard() AgentCard {
	// Allow the agent URL to be configured via environment variable for deployment flexibility.
	agentURL := os.Getenv("AGENT_URL")
	if agentURL == "" {
		agentURL = "http://localhost:8888"
	}

	return AgentCard{
		Name:        "Security Compliance Validator",
		Description: "Go-based validation engine that checks vendor contracts against corporate compliance policy rules. Accepts extracted contract fields and returns pass/fail verdict with specific violations.",
		Version:     "1.0.0",
		SupportedInterfaces: []AgentInterface{
			{
				URL:             agentURL,
				ProtocolBinding: "JSONRPC",
				ProtocolVersion: "1.0",
			},
		},
		Capabilities: Capabilities{
			ExtendedAgentCard: false,
		},
		DefaultInputModes:  []string{"application/json"},
		DefaultOutputModes: []string{"application/json"},
		Skills: []Skill{
			{
				ID:          "contract_compliance_check",
				Name:        "Contract Compliance Check",
				Description: "Validates extracted contract fields against corporate policy rules. Returns pass/fail verdict with specific violations.",
				Tags:        []string{"compliance", "contract", "validation"},
				Examples: []string{
					"Check this contract for compliance violations",
					"Validate vendor agreement terms against policy",
				},
			},
		},
	}
}

// Handler serves agent card configurations as JSON objects.
func Handler(w http.ResponseWriter, r *http.Request) {
	card := GetCard()
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(card)
}
