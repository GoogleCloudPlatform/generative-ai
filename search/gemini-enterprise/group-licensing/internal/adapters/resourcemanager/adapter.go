package resourcemanager

import (
	"context"
	"fmt"
	"strings"

	cloudresourcemanager "google.golang.org/api/cloudresourcemanager/v3"

	"github.com/cloud-gtm/gemini-box-office/internal/ports"
)

var _ ports.ResourceManagerClient = (*Adapter)(nil)

// Adapter implements ports.ResourceManagerClient using the Cloud Resource
// Manager API v3.
type Adapter struct {
	svc *cloudresourcemanager.Service
}

// New constructs an Adapter from an already-authenticated
// *cloudresourcemanager.Service. The caller is responsible for configuring
// Application Default Credentials before calling New.
func New(svc *cloudresourcemanager.Service) *Adapter {
	return &Adapter{svc: svc}
}

// ResolveProjectNumber returns the numeric project number for the given project
// ID by calling projects.get on the Resource Manager API. The returned string
// contains only the number (e.g. "415104041262"), with the "projects/" prefix
// stripped.
func (a *Adapter) ResolveProjectNumber(ctx context.Context, projectID string) (string, error) {
	project, err := a.svc.Projects.Get("projects/"+projectID).Context(ctx).Do()
	if err != nil {
		return "", fmt.Errorf("resolving project number for %q: %w", projectID, err)
	}
	// project.Name has the form "projects/415104041262".
	number := strings.TrimPrefix(project.Name, "projects/")
	return number, nil
}
