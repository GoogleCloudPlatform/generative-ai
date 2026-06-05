package compliance

import (
	"strings"
	"testing"
)

func TestCheckCompliance_Pass(t *testing.T) {
	policy := Policy{
		MaxContractValue:         500000.0,
		ProhibitedClauses:        []string{"unlimited liability", "auto-renewal > 3yr"},
		RequiredInsuranceMinimum: 1000000.0,
		MaxTermYears:             5,
		RequiredTerminationClause: true,
	}

	// Acme Cloud Solutions values (Should Pass)
	contract := ContractDetails{
		ContractValue:        250000.0,
		ContractorName:       "Acme Cloud Solutions",
		ClientName:           "GFD Platform Systems",
		StartDate:            "2026-06-01",
		EndDate:              "2028-06-01",
		LiabilityLimit:       "$1,000,000.00 standard cap",
		InsuranceCoverage:    2000000.0,
		AutoRenewal:          false,
		HasTerminationClause: true,
		TermLengthYears:      2,
	}

	result := CheckCompliance(contract, policy)
	if !result.Passed {
		t.Errorf("Expected compliance check to PASS, but got FAIL. Violations: %v", result.Violations)
	}
	if len(result.Violations) != 0 {
		t.Errorf("Expected 0 violations, got %d: %v", len(result.Violations), result.Violations)
	}
}

func TestCheckCompliance_UnlimitedLiability(t *testing.T) {
	policy := Policy{
		MaxContractValue:         500000.0,
		ProhibitedClauses:        []string{"unlimited liability"},
		RequiredInsuranceMinimum: 1000000.0,
		MaxTermYears:             5,
		RequiredTerminationClause: true,
	}

	// Apex Data Systems (Should Fail due to unlimited liability)
	contract := ContractDetails{
		ContractValue:        450000.0,
		ContractorName:       "Apex Data Systems",
		ClientName:           "GFD Platform Systems",
		StartDate:            "2026-06-01",
		EndDate:              "2027-06-01",
		LiabilityLimit:       "Contractor liability shall be entirely unlimited under all conditions",
		InsuranceCoverage:    1500000.0,
		AutoRenewal:          false,
		HasTerminationClause: true,
		TermLengthYears:      1,
	}

	result := CheckCompliance(contract, policy)
	if result.Passed {
		t.Errorf("Expected compliance check to FAIL, but got PASS.")
	}

	hasLiabilityViolation := false
	for _, v := range result.Violations {
		if strings.Contains(v, "Unlimited contractor liability") {
			hasLiabilityViolation = true
		}
	}
	if !hasLiabilityViolation {
		t.Errorf("Expected unlimited liability violation, but got none in: %v", result.Violations)
	}
}

func TestCheckCompliance_MultiViolations(t *testing.T) {
	policy := Policy{
		MaxContractValue:         500000.0,
		ProhibitedClauses:        []string{"unlimited liability", "auto-renewal > 3yr"},
		RequiredInsuranceMinimum: 1000000.0,
		MaxTermYears:             5,
		RequiredTerminationClause: true,
	}

	// Legacy Networks Corp — triggers all 6 violations:
	// 1. Contract value exceeds limit
	// 2. Unlimited liability (waived)
	// 3. Auto-renewal > 3yr
	// 4. Insurance below minimum
	// 5. Term length exceeds max
	// 6. Missing termination clause
	contract := ContractDetails{
		ContractValue:        850000.0,
		ContractorName:       "Legacy Networks Corp",
		ClientName:           "GFD Platform Systems",
		StartDate:            "2026-06-01",
		EndDate:              "2032-06-01",
		LiabilityLimit:       "Contractor GFD liability limits are waived, resulting in unlimited GFD exposure",
		InsuranceCoverage:    500000.0,
		AutoRenewal:          true,
		HasTerminationClause: false,
		TermLengthYears:      6,
	}

	result := CheckCompliance(contract, policy)
	if result.Passed {
		t.Errorf("Expected compliance check to FAIL, but got PASS.")
	}

	expectedViolations := 6
	if len(result.Violations) != expectedViolations {
		t.Errorf("Expected %d violations, got %d: %v", expectedViolations, len(result.Violations), result.Violations)
	}
}
