/*
Copyright © 2026 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

	http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package models

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestSKU_IsValid(t *testing.T) {
	tests := []struct {
		name string
		sku  SKU
		want bool
	}{
		{"search and assistant is valid", SKUSearchAndAssistant, true},
		{"enterprise is valid", SKUEnterprise, true},
		{"search is valid", SKUSearch, true},
		{"notebook LM is valid", SKUNotebookLM, true},
		{"agentspace business is valid", SKUAgentspaceBusiness, true},
		{"agentspace starter is valid", SKUAgentspaceStarter, true},
		{"frontline worker is valid", SKUFrontlineWorker, true},
		{"frontline starter is valid", SKUFrontlineStarter, true},
		{"enterprise emerging is valid", SKUEnterpriseEmerging, true},
		{"edu pro is valid", SKUEduPro, true},
		{"edu is valid", SKUEdu, true},
		{"edu pro emerging is valid", SKUEduProEmerging, true},
		{"edu emerging is valid", SKUEduEmerging, true},
		{"unspecified is invalid", SKUUnspecified, false},
		{"empty string is invalid", SKU(""), false},
		{"arbitrary string is invalid", SKU("GEMINI_UNKNOWN"), false},
		{"old SKU name is invalid", SKU("GEMINI_ENTERPRISE"), false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.want, tt.sku.IsValid())
		})
	}
}

func TestSKU_Precedence(t *testing.T) {
	tests := []struct {
		name string
		sku  SKU
		want int
	}{
		{"search and assistant has precedence 13", SKUSearchAndAssistant, 13},
		{"enterprise has precedence 12", SKUEnterprise, 12},
		{"search has precedence 11", SKUSearch, 11},
		{"notebook LM has precedence 10", SKUNotebookLM, 10},
		{"agentspace business has precedence 9", SKUAgentspaceBusiness, 9},
		{"agentspace starter has precedence 8", SKUAgentspaceStarter, 8},
		{"frontline worker has precedence 7", SKUFrontlineWorker, 7},
		{"frontline starter has precedence 6", SKUFrontlineStarter, 6},
		{"enterprise emerging has precedence 5", SKUEnterpriseEmerging, 5},
		{"edu pro has precedence 4", SKUEduPro, 4},
		{"edu has precedence 3", SKUEdu, 3},
		{"edu pro emerging has precedence 2", SKUEduProEmerging, 2},
		{"edu emerging has precedence 1", SKUEduEmerging, 1},
		{"unspecified has precedence 0", SKUUnspecified, 0},
		{"unknown has precedence 0", SKU("UNKNOWN"), 0},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.want, tt.sku.Precedence())
		})
	}
}

func TestSKU_PrecedenceOrdering(t *testing.T) {
	// Verify strict total ordering from highest to lowest precedence.
	ordered := []SKU{
		SKUSearchAndAssistant,
		SKUEnterprise,
		SKUSearch,
		SKUNotebookLM,
		SKUAgentspaceBusiness,
		SKUAgentspaceStarter,
		SKUFrontlineWorker,
		SKUFrontlineStarter,
		SKUEnterpriseEmerging,
		SKUEduPro,
		SKUEdu,
		SKUEduProEmerging,
		SKUEduEmerging,
	}

	for i := 0; i < len(ordered)-1; i++ {
		higher := ordered[i]
		lower := ordered[i+1]
		assert.Greater(t, higher.Precedence(), lower.Precedence(),
			"expected %q (%d) to have higher precedence than %q (%d)",
			higher, higher.Precedence(), lower, lower.Precedence())
	}
}

func TestSKU_HasHigherPrecedenceThan(t *testing.T) {
	tests := []struct {
		name  string
		s     SKU
		other SKU
		want  bool
	}{
		{"search_and_assistant > enterprise", SKUSearchAndAssistant, SKUEnterprise, true},
		{"search_and_assistant > agentspace_business", SKUSearchAndAssistant, SKUAgentspaceBusiness, true},
		{"search_and_assistant > frontline_worker", SKUSearchAndAssistant, SKUFrontlineWorker, true},
		{"enterprise > agentspace_business", SKUEnterprise, SKUAgentspaceBusiness, true},
		{"enterprise > frontline_worker", SKUEnterprise, SKUFrontlineWorker, true},
		{"search > agentspace_business", SKUSearch, SKUAgentspaceBusiness, true},
		{"notebook_lm > agentspace_business", SKUNotebookLM, SKUAgentspaceBusiness, true},
		{"agentspace_business > frontline_worker", SKUAgentspaceBusiness, SKUFrontlineWorker, true},
		{"agentspace_starter above enterprise_emerging", SKUAgentspaceStarter, SKUEnterpriseEmerging, true},
		{"frontline_starter above enterprise_emerging", SKUFrontlineStarter, SKUEnterpriseEmerging, true},
		{"enterprise_emerging > edu_pro", SKUEnterpriseEmerging, SKUEduPro, true},
		{"edu_pro > edu", SKUEduPro, SKUEdu, true},
		{"edu > edu_pro_emerging", SKUEdu, SKUEduProEmerging, true},
		{"edu_pro_emerging > edu_emerging", SKUEduProEmerging, SKUEduEmerging, true},
		{"frontline_worker not > enterprise", SKUFrontlineWorker, SKUEnterprise, false},
		{"agentspace_business not > search", SKUAgentspaceBusiness, SKUSearch, false},
		{"edu_emerging not > enterprise_emerging", SKUEduEmerging, SKUEnterpriseEmerging, false},
		{"same SKU not > itself", SKUEnterprise, SKUEnterprise, false},
		{"unknown not > frontline_worker", SKU("UNKNOWN"), SKUFrontlineWorker, false},
		{"frontline_worker > unknown", SKUFrontlineWorker, SKU("UNKNOWN"), true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.want, tt.s.HasHigherPrecedenceThan(tt.other))
		})
	}
}

func TestWorkflowType_Values(t *testing.T) {
	assert.Equal(t, WorkflowType("joiner"), WorkflowJoiner)
	assert.Equal(t, WorkflowType("garbage_collection"), WorkflowGarbageCollection)
}

func TestLicenseState_Values(t *testing.T) {
	assert.Equal(t, LicenseState("ASSIGNED"), LicenseStateAssigned)
	assert.Equal(t, LicenseState("REVOKED"), LicenseStateRevoked)
}

func TestLicenseAction_Values(t *testing.T) {
	assert.Equal(t, LicenseAction("GRANT"), LicenseActionGrant)
	assert.Equal(t, LicenseAction("REVOKE"), LicenseActionRevoke)
}

func TestMemberType_Values(t *testing.T) {
	assert.Equal(t, MemberType("USER"), MemberTypeUser)
	assert.Equal(t, MemberType("GROUP"), MemberTypeGroup)
}
