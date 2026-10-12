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

package tools_test

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"local-code-assistant/tools"
)

func TestRegistry(t *testing.T) {
	reg := tools.NewRegistry(
		tools.NewListDirectory(),
		tools.NewReadFile(),
		tools.NewGraphviz("testdata"),
	)

	decls := reg.Declarations()
	if len(decls) != 3 {
		t.Fatalf("expected 3 declarations, got %d", len(decls))
	}

	// Unknown tool execution
	res := reg.Execute(context.Background(), "non_existent_tool", nil)
	if res["error"] == nil {
		t.Errorf("expected error for nonexistent tool, got nil")
	}
}

func TestListDirectoryTool(t *testing.T) {
	tempDir := t.TempDir()
	_ = os.WriteFile(filepath.Join(tempDir, "file1.txt"), []byte("hello"), 0644)
	_ = os.Mkdir(filepath.Join(tempDir, "subdir"), 0755)

	tool := tools.NewListDirectory()
	res, err := tool.Execute(context.Background(), map[string]any{"path": tempDir})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	files, ok := res["output"].([]string)
	if !ok || len(files) != 2 {
		t.Fatalf("expected 2 files in output, got: %v", res["output"])
	}
}

func TestReadFileTool(t *testing.T) {
	tempDir := t.TempDir()
	filePath := filepath.Join(tempDir, "sample.go")
	shortContent := "package main\n\nfunc main() {}\n"
	_ = os.WriteFile(filePath, []byte(shortContent), 0644)

	tool := tools.NewReadFile()

	// 1. Normal read
	res, err := tool.Execute(context.Background(), map[string]any{"path": filePath})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if res["output"] != shortContent {
		t.Errorf("expected %q, got %q", shortContent, res["output"])
	}

	// 2. Truncation test (> 10KB)
	largePath := filepath.Join(tempDir, "large.txt")
	largeData := strings.Repeat("a", 12000)
	_ = os.WriteFile(largePath, []byte(largeData), 0644)

	res, err = tool.Execute(context.Background(), map[string]any{"path": largePath})
	if err != nil {
		t.Fatalf("unexpected error on large file: %v", err)
	}
	if res["truncated"] != true {
		t.Errorf("expected truncated == true for >10KB file")
	}
	outputStr := res["output"].(string)
	if !strings.Contains(outputStr, "[truncated to protect context window]") {
		t.Errorf("expected truncation notice in output")
	}
}

func TestGraphvizTool(t *testing.T) {
	tempDir := t.TempDir()
	tool := tools.NewGraphviz(tempDir)

	dotCode := `digraph TestArch {
		rankdir=LR;
		node [shape=box];
		Client -> Server -> Database;
	}`

	res, err := tool.Execute(context.Background(), map[string]any{
		"dot_code": dotCode,
		"filename": "test_arch",
		"title":    "Test Architecture",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if res["success"] != true {
		t.Fatalf("expected success == true, got: %v", res)
	}

	dotPath, _ := res["dot_path"].(string)
	pngPath, _ := res["png_path"].(string)
	b64, _ := res["image_base64"].(string)

	if !strings.HasSuffix(dotPath, "test_arch.dot") {
		t.Errorf("expected .dot file path, got %s", dotPath)
	}
	if !strings.HasSuffix(pngPath, "test_arch.png") {
		t.Errorf("expected .png file path, got %s", pngPath)
	}
	if !strings.HasPrefix(b64, "data:image/png;base64,") {
		t.Errorf("expected base64 data URL prefix, got %s", b64[:30])
	}

	// Check that files exist on disk
	if _, err := os.Stat(dotPath); err != nil {
		t.Errorf(".dot file was not created: %v", err)
	}
	if _, err := os.Stat(pngPath); err != nil {
		t.Errorf(".png file was not created: %v", err)
	}
}
