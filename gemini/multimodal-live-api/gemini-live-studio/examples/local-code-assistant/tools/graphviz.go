// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package tools

import (
	"context"
	"encoding/base64"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"google.golang.org/genai"
)

var filenameSanitizer = regexp.MustCompile(`[^a-zA-Z0-9_\-]+`)

// GraphvizTool renders Graphviz DOT source code into .dot files and .png images.
type GraphvizTool struct {
	outputDir string
}

// NewGraphviz creates a new GraphvizTool that writes files to the specified directory.
func NewGraphviz(outputDir string) *GraphvizTool {
	if outputDir == "" {
		outputDir = "diagrams"
	}
	return &GraphvizTool{outputDir: outputDir}
}

func (t *GraphvizTool) Name() string {
	return "generate_diagram"
}

func (t *GraphvizTool) Declaration() *genai.FunctionDeclaration {
	return &genai.FunctionDeclaration{
		Name:        t.Name(),
		Description: "Generate an architecture, sequence, flowchart, or technical diagram using Graphviz DOT syntax. Creates a .dot file and compiles it to a PNG image that is displayed in the UI.",
		Parameters: &genai.Schema{
			Type: genai.TypeObject,
			Properties: map[string]*genai.Schema{
				"dot_code": {
					Type:        genai.TypeString,
					Description: "Valid Graphviz DOT source code representing the diagram (e.g., 'digraph G { rankdir=LR; NodeA -> NodeB; }'). Use standard attributes like shape, style, fillcolor, and color for clear visual presentation.",
				},
				"filename": {
					Type:        genai.TypeString,
					Description: "Base name for the diagram file without extension (e.g. 'system_architecture', 'auth_sequence'). If omitted, a timestamped name is used.",
				},
				"title": {
					Type:        genai.TypeString,
					Description: "Human-readable title or caption for the diagram (e.g. 'System Architecture Overview').",
				},
			},
			Required: []string{"dot_code"},
		},
	}
}

func (t *GraphvizTool) Execute(ctx context.Context, args map[string]any) (map[string]any, error) {
	dotCode, ok := args["dot_code"].(string)
	if !ok || strings.TrimSpace(dotCode) == "" {
		return nil, errors.New("dot_code argument is required and cannot be empty")
	}

	title, _ := args["title"].(string)
	if title == "" {
		title = "Technical Diagram"
	}

	rawFilename, _ := args["filename"].(string)
	rawFilename = strings.TrimSuffix(rawFilename, ".dot")
	rawFilename = strings.TrimSuffix(rawFilename, ".png")
	cleanFilename := filenameSanitizer.ReplaceAllString(rawFilename, "_")
	cleanFilename = strings.Trim(cleanFilename, "_")
	if cleanFilename == "" {
		cleanFilename = fmt.Sprintf("diagram_%d", time.Now().Unix())
	}

	if err := os.MkdirAll(t.outputDir, 0755); err != nil {
		return nil, fmt.Errorf("creating diagrams directory: %w", err)
	}

	dotPath := filepath.Join(t.outputDir, cleanFilename+".dot")
	pngPath := filepath.Join(t.outputDir, cleanFilename+".png")

	// 1. Write the .dot source file
	if err := os.WriteFile(dotPath, []byte(dotCode), 0644); err != nil {
		return nil, fmt.Errorf("writing .dot file %q: %w", dotPath, err)
	}

	// 2. Locate Graphviz 'dot' binary
	dotBin, err := exec.LookPath("dot")
	if err != nil {
		return map[string]any{
			"error":    "Graphviz 'dot' binary not found in PATH. The .dot file was saved, but PNG rendering requires Graphviz. Please install Graphviz (e.g., 'brew install graphviz' or 'sudo apt-get install graphviz').",
			"dot_path": dotPath,
			"dot_code": dotCode,
			"title":    title,
			"hint":     "Install Graphviz using 'brew install graphviz' to enable automatic PNG generation.",
		}, nil
	}

	// 3. Compile .dot to .png via dot CLI
	cmd := exec.CommandContext(ctx, dotBin, "-Tpng", dotPath, "-o", pngPath)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return map[string]any{
			"error":    fmt.Sprintf("Graphviz compilation error: %s (exit: %v)", strings.TrimSpace(string(output)), err),
			"dot_path": dotPath,
			"dot_code": dotCode,
			"title":    title,
		}, nil
	}

	// 4. Read generated PNG and encode to Base64
	pngBytes, err := os.ReadFile(pngPath)
	if err != nil {
		return nil, fmt.Errorf("reading rendered PNG %q: %w", pngPath, err)
	}

	b64Image := "data:image/png;base64," + base64.StdEncoding.EncodeToString(pngBytes)
	imageURL := "/diagrams/" + filepath.Base(pngPath)

	return map[string]any{
		"success":      true,
		"title":        title,
		"filename":     cleanFilename,
		"dot_path":     dotPath,
		"png_path":     pngPath,
		"image_url":    imageURL,
		"image_base64": b64Image,
		"dot_code":     dotCode,
		"output":       fmt.Sprintf("Successfully generated diagram %q at %s and %s", title, dotPath, pngPath),
	}, nil
}
