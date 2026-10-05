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
	"errors"
	"fmt"
	"os"

	"google.golang.org/genai"
)

const maxReadFileBytes = 10000

// ListDirectoryTool provides filesystem directory listing capabilities.
type ListDirectoryTool struct{}

// NewListDirectory creates a new ListDirectoryTool.
func NewListDirectory() *ListDirectoryTool {
	return &ListDirectoryTool{}
}

func (t *ListDirectoryTool) Name() string {
	return "list_directory"
}

func (t *ListDirectoryTool) Declaration() *genai.FunctionDeclaration {
	return &genai.FunctionDeclaration{
		Name:        t.Name(),
		Description: "List files and folders in a local workspace directory.",
		Parameters: &genai.Schema{
			Type: genai.TypeObject,
			Properties: map[string]*genai.Schema{
				"path": {
					Type:        genai.TypeString,
					Description: "The relative or absolute path of the directory. E.g. '.', 'frontend/', '../'. Defaults to current directory.",
				},
			},
		},
	}
}

func (t *ListDirectoryTool) Execute(_ context.Context, args map[string]any) (map[string]any, error) {
	dirPath := "."
	if p, ok := args["path"].(string); ok && p != "" {
		dirPath = p
	}

	entries, err := os.ReadDir(dirPath)
	if err != nil {
		return nil, fmt.Errorf("reading directory %q: %w", dirPath, err)
	}

	var names []string
	for _, entry := range entries {
		name := entry.Name()
		if entry.IsDir() {
			name += "/"
		}
		names = append(names, name)
	}

	return map[string]any{
		"path":   dirPath,
		"output": names,
	}, nil
}

// ReadFileTool provides file reading capabilities with a token safety truncation guardrail.
type ReadFileTool struct{}

// NewReadFile creates a new ReadFileTool.
func NewReadFile() *ReadFileTool {
	return &ReadFileTool{}
}

func (t *ReadFileTool) Name() string {
	return "read_file"
}

func (t *ReadFileTool) Declaration() *genai.FunctionDeclaration {
	return &genai.FunctionDeclaration{
		Name:        t.Name(),
		Description: "Read the text contents of a file. Content exceeding 10KB is truncated to protect the context window.",
		Parameters: &genai.Schema{
			Type: genai.TypeObject,
			Properties: map[string]*genai.Schema{
				"path": {
					Type:        genai.TypeString,
					Description: "The path of the file to read (relative or absolute).",
				},
			},
			Required: []string{"path"},
		},
	}
}

func (t *ReadFileTool) Execute(_ context.Context, args map[string]any) (map[string]any, error) {
	filePath, ok := args["path"].(string)
	if !ok || filePath == "" {
		return nil, errors.New("path argument is required and must be a non-empty string")
	}

	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("reading file %q: %w", filePath, err)
	}

	content := string(data)
	truncated := false
	if len(content) > maxReadFileBytes {
		content = content[:maxReadFileBytes] + "\n...[truncated to protect context window]"
		truncated = true
	}

	return map[string]any{
		"path":      filePath,
		"output":    content,
		"truncated": truncated,
	}, nil
}
