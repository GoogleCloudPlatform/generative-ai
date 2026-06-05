package compliance

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"
)

// Policy represents compliance validation rules configuration.
type Policy struct {
	MaxContractValue           float64  `json:"max_contract_value"`
	ProhibitedClauses          []string `json:"prohibited_clauses"`
	RequiredInsuranceMinimum   float64  `json:"required_insurance_minimum"`
	MaxTermYears               int      `json:"max_term_years"`
	RequiredTerminationClause  bool     `json:"required_termination_clause"`
}

// ContractDetails matches legal fields extracted by the Python subagent.
type ContractDetails struct {
	ContractValue        float64 `json:"contract_value"`
	ContractorName       string  `json:"contractor_name"`
	ClientName           string  `json:"client_name"`
	StartDate            string  `json:"start_date"`
	EndDate              string  `json:"end_date"`
	LiabilityLimit       string  `json:"liability_limit"`
	InsuranceCoverage    float64 `json:"insurance_coverage"`
	AutoRenewal          bool    `json:"auto_renewal"`
	HasTerminationClause bool    `json:"has_termination_clause"`
	TermLengthYears      int     `json:"term_length_years"`
}

// ComplianceResult holds safety pass audit verdicts and violation details.
type ComplianceResult struct {
	Passed           bool     `json:"passed"`
	Violations       []string `json:"violations"`
	VerdictTimestamp string   `json:"verdict_timestamp"`
}

// LoadPolicy reads legal policy metrics from local file paths.
func LoadPolicy(path string) (Policy, error) {
	var policy Policy
	bytes, err := os.ReadFile(path)
	if err != nil {
		return policy, fmt.Errorf("error reading policy file: %w", err)
	}
	err = json.Unmarshal(bytes, &policy)
	if err != nil {
		return policy, fmt.Errorf("error decoding policy JSON: %w", err)
	}
	return policy, nil
}

// CheckCompliance evaluates contract parameters against standard corporate policies.
func CheckCompliance(details ContractDetails, policy Policy) ComplianceResult {
	violations := make([]string, 0)

	// 1. Contract Value Audit
	if details.ContractValue > policy.MaxContractValue {
		violations = append(violations, fmt.Sprintf(
			"Contract value $%.2f exceeds company framework limit of $%.2f",
			details.ContractValue, policy.MaxContractValue,
		))
	}

	// 2. Prohibited Clauses (Unlimited liability checks)
	liabilityUpper := strings.ToLower(details.LiabilityLimit)
	for _, clause := range policy.ProhibitedClauses {
		if clause == "unlimited liability" {
			if strings.Contains(liabilityUpper, "unlimited") || strings.Contains(liabilityUpper, "waived") {
				violations = append(violations, "Unlimited contractor liability clauses are strictly prohibited by company policy")
			}
		}
		if clause == "auto-renewal > 3yr" && details.AutoRenewal && details.TermLengthYears > 3 {
			violations = append(violations, "Auto-renewal spans extending beyond 3 years are unauthorized without general counsel signatures")
		}
	}

	// 3. Liability Insurance Bounds Check
	if details.InsuranceCoverage < policy.RequiredInsuranceMinimum {
		violations = append(violations, fmt.Sprintf(
			"Insurance coverage $%.2f is under the security minimum threshold of $%.2f",
			details.InsuranceCoverage, policy.RequiredInsuranceMinimum,
		))
	}

	// 4. Term Length Limits
	if details.TermLengthYears > policy.MaxTermYears {
		violations = append(violations, fmt.Sprintf(
			"Engagement length of %d years exceeds framework limit bounds of %d years",
			details.TermLengthYears, policy.MaxTermYears,
		))
	}

	// 5. Written Exit Notice Audit
	if policy.RequiredTerminationClause && !details.HasTerminationClause {
		violations = append(violations, "Missing required written exit termination safety clauses")
	}

	passed := len(violations) == 0
	return ComplianceResult{
		Passed:           passed,
		Violations:       violations,
		VerdictTimestamp: time.Now().UTC().Format(time.RFC3339),
	}
}
