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

// SKU represents a Gemini Enterprise subscription tier identifier as returned
// by the Discovery Engine API.
type SKU string

const (
	SKUSearchAndAssistant SKU = "SUBSCRIPTION_TIER_SEARCH_AND_ASSISTANT" // Gemini Enterprise Plus tier.
	SKUEnterprise         SKU = "SUBSCRIPTION_TIER_ENTERPRISE"           // Gemini Enterprise Standard tier.
	SKUSearch             SKU = "SUBSCRIPTION_TIER_SEARCH"               // Search + NotebookLM tier.
	SKUNotebookLM         SKU = "SUBSCRIPTION_TIER_NOTEBOOK_LM"          // NotebookLM-only tier.
	SKUAgentspaceBusiness SKU = "SUBSCRIPTION_TIER_AGENTSPACE_BUSINESS"  // Gemini Business tier.
	SKUAgentspaceStarter  SKU = "SUBSCRIPTION_TIER_AGENTSPACE_STARTER"   // Gemini Business Starter tier.
	SKUFrontlineWorker    SKU = "SUBSCRIPTION_TIER_FRONTLINE_WORKER"     // Gemini Frontline Worker tier.
	SKUFrontlineStarter   SKU = "SUBSCRIPTION_TIER_FRONTLINE_STARTER"    // Gemini Frontline Starter tier.
	SKUEnterpriseEmerging SKU = "SUBSCRIPTION_TIER_ENTERPRISE_EMERGING"  // Gemini Enterprise Standard — emerging markets.
	SKUEduPro             SKU = "SUBSCRIPTION_TIER_EDU_PRO"              // Gemini Enterprise EDU Pro tier.
	SKUEdu                SKU = "SUBSCRIPTION_TIER_EDU"                  // Gemini Enterprise EDU tier.
	SKUEduProEmerging     SKU = "SUBSCRIPTION_TIER_EDU_PRO_EMERGING"     // Gemini Enterprise EDU Pro — emerging markets.
	SKUEduEmerging        SKU = "SUBSCRIPTION_TIER_EDU_EMERGING"         // Gemini Enterprise EDU — emerging markets.
	SKUUnspecified        SKU = "SUBSCRIPTION_TIER_UNSPECIFIED"          // Default/unset value.
)

// skuPrecedence maps each SKU to its precedence rank. Higher value = higher
// precedence. SUBSCRIPTION_TIER_UNSPECIFIED is not included and returns 0 by
// default, the same as any unrecognised value.
var skuPrecedence = map[SKU]int{
	SKUSearchAndAssistant: 13,
	SKUEnterprise:         12,
	SKUSearch:             11,
	SKUNotebookLM:         10,
	SKUAgentspaceBusiness: 9,
	SKUAgentspaceStarter:  8,
	SKUFrontlineWorker:    7,
	SKUFrontlineStarter:   6,
	SKUEnterpriseEmerging: 5,
	SKUEduPro:             4,
	SKUEdu:                3,
	SKUEduProEmerging:     2,
	SKUEduEmerging:        1,
}

// IsValid reports whether s is one of the four recognized SKU values.
func (s SKU) IsValid() bool {
	_, ok := skuPrecedence[s]
	return ok
}

// Precedence returns the numeric precedence of the SKU.
// A higher value indicates a higher-tier entitlement.
// Returns 0 for unrecognized SKUs.
func (s SKU) Precedence() int {
	return skuPrecedence[s]
}

// HasHigherPrecedenceThan reports whether s outranks other.
func (s SKU) HasHigherPrecedenceThan(other SKU) bool {
	return s.Precedence() > other.Precedence()
}

// WorkflowType identifies which reconciliation workflow is executing.
type WorkflowType string

const (
	WorkflowJoiner            WorkflowType = "joiner"
	WorkflowGarbageCollection WorkflowType = "garbage_collection"
)

// LicenseState represents the current state of a user license as returned
// by the Discovery Engine API.
type LicenseState string

const (
	LicenseStateAssigned LicenseState = "ASSIGNED"
	LicenseStateRevoked  LicenseState = "REVOKED"
)

// LicenseAction represents the operation to apply during batchUpdateUserLicenses.
type LicenseAction string

const (
	LicenseActionGrant  LicenseAction = "GRANT"
	LicenseActionRevoke LicenseAction = "REVOKE"
)

// Location represents the geographic region where Gemini licenses are managed.
type Location string

const (
	LocationGlobal Location = "global"
	LocationUS     Location = "us"
	LocationEU     Location = "eu"
)

var validLocations = map[Location]bool{
	LocationGlobal: true,
	LocationUS:     true,
	LocationEU:     true,
}

// IsValid reports whether l is one of the three recognized location values.
func (l Location) IsValid() bool {
	return validLocations[l]
}

// MemberType classifies a Cloud Identity group member as returned by members.list.
type MemberType string

const (
	MemberTypeUser  MemberType = "USER"
	MemberTypeGroup MemberType = "GROUP"
)
