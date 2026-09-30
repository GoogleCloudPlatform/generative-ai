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

package ui

import (
	"fmt"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/GoogleCloudPlatform/generative-ai/gemini/agentic-video/gemini-agentic-video-go/internal/runner"
	"github.com/charmbracelet/lipgloss"
	"github.com/mattn/go-isatty"
)

var (
	badgeRunning   = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#000000")).Background(ColorGeminiCyan).Padding(0, 1).Render("RUNNING")
	badgeCompleted = lipgloss.NewStyle().Bold(true).Foreground(ColorWhite).Background(ColorSuccess).Padding(0, 1).Render("COMPLETED")
	badgeFailed    = lipgloss.NewStyle().Bold(true).Foreground(ColorWhite).Background(ColorDanger).Padding(0, 1).Render("FAILED")
)

// BenchmarkTracker manages live concurrent terminal telemetry for side-by-side benchmark runs.
type BenchmarkTracker struct {
	isTTY        bool
	startTime    time.Time
	mu           sync.Mutex
	agenticDone  bool
	agenticRes   *runner.Result
	agenticErr   error
	staticDone   bool
	staticRes    *runner.Result
	staticErr    error
	stopChan     chan struct{}
	doneChan     chan struct{}
	thinking     string
	hasDrawnOnce bool
}

// NewBenchmarkTracker initializes a concurrent benchmark progress tracker.
func NewBenchmarkTracker(thinking string) *BenchmarkTracker {
	fd := os.Stdout.Fd()
	isTerminal := isatty.IsTerminal(fd) || isatty.IsCygwinTerminal(fd)

	return &BenchmarkTracker{
		isTTY:     isTerminal,
		thinking:  thinking,
		stopChan:  make(chan struct{}),
		doneChan:  make(chan struct{}),
		startTime: time.Now(),
	}
}

// Start initiates the live 100ms terminal ticker loop.
func (bt *BenchmarkTracker) Start() {
	bt.startTime = time.Now()

	fmt.Println(SectionHeader.Render("🏎️  LIVE CONCURRENT BENCHMARK SHOOTOUT (Parallel Goroutines)"))
	if !bt.isTTY {
		fmt.Printf("[%s] Both pipelines dispatched concurrently in parallel goroutines...\n", bt.formatElapsed(0))
		return
	}

	go func() {
		defer close(bt.doneChan)
		ticker := time.NewTicker(100 * time.Millisecond)
		defer ticker.Stop()

		for {
			select {
			case <-bt.stopChan:
				bt.redraw(true)
				return
			case <-ticker.C:
				bt.redraw(false)
			}
		}
	}()
}

// Update records pipeline completion and updates the live display state.
func (bt *BenchmarkTracker) Update(agenticDone, staticDone bool, aRes, sRes *runner.Result) {
	bt.mu.Lock()
	defer bt.mu.Unlock()

	if agenticDone && !bt.agenticDone {
		bt.agenticDone = true
		bt.agenticRes = aRes
		if !bt.isTTY {
			tokStr := "0"
			if aRes != nil && aRes.Usage != nil {
				tokStr = fmt.Sprintf("%d", aRes.Usage.TotalTokenCount)
			}
			fmt.Printf("[%s] ⚡ Agentic Video COMPLETED in %v (Tokens: %s)\n",
				bt.formatElapsed(time.Since(bt.startTime)),
				aRes.Duration.Round(time.Millisecond),
				tokStr)
		}
	}

	if staticDone && !bt.staticDone {
		bt.staticDone = true
		bt.staticRes = sRes
		if !bt.isTTY {
			tokStr := "0"
			if sRes != nil && sRes.Usage != nil {
				tokStr = fmt.Sprintf("%d", sRes.Usage.TotalTokenCount)
			}
			fmt.Printf("[%s] 🐢 Static 1-FPS COMPLETED in %v (Tokens: %s)\n",
				bt.formatElapsed(time.Since(bt.startTime)),
				sRes.Duration.Round(time.Millisecond),
				tokStr)
		}
	}
}

// SetErrors records execution errors for pipelines if any occur.
func (bt *BenchmarkTracker) SetErrors(agenticErr, staticErr error) {
	bt.mu.Lock()
	defer bt.mu.Unlock()
	bt.agenticErr = agenticErr
	bt.staticErr = staticErr
}

// Stop terminates the ticker and leaves the terminal in a clean state.
func (bt *BenchmarkTracker) Stop() {
	if !bt.isTTY {
		return
	}
	close(bt.stopChan)
	<-bt.doneChan
	fmt.Println()
}

func (bt *BenchmarkTracker) redraw(isFinal bool) {
	bt.mu.Lock()
	defer bt.mu.Unlock()

	elapsed := time.Since(bt.startTime).Round(100 * time.Millisecond)

	// Agentic Status Line
	var aStatus, aDetails string
	if bt.agenticErr != nil {
		aStatus = badgeFailed
		aDetails = MutedStyle.Render(fmt.Sprintf("Error: %v", bt.agenticErr))
	} else if bt.agenticDone && bt.agenticRes != nil {
		aStatus = badgeCompleted
		tokens := int32(0)
		if bt.agenticRes.Usage != nil {
			tokens = bt.agenticRes.Usage.TotalTokenCount
		}
		aDetails = fmt.Sprintf("%-7s • %s tokens %s",
			GreenStyle.Render(fmt.Sprintf("%v", bt.agenticRes.Duration.Round(time.Millisecond))),
			BoldWhite.Render(fmt.Sprintf("%d", tokens)),
			MutedStyle.Render("(dynamic frame inspection)"),
		)
	} else {
		aStatus = badgeRunning
		aDetails = fmt.Sprintf("%-7s • %s",
			CyanStyle.Render(fmt.Sprintf("%v", elapsed)),
			MutedStyle.Render("seeking & inspecting timeline chunks..."),
		)
	}

	// Static Status Line
	var sStatus, sDetails string
	if bt.staticErr != nil {
		sStatus = badgeFailed
		sDetails = MutedStyle.Render(fmt.Sprintf("Error: %v", bt.staticErr))
	} else if bt.staticDone && bt.staticRes != nil {
		sStatus = badgeCompleted
		tokens := int32(0)
		if bt.staticRes.Usage != nil {
			tokens = bt.staticRes.Usage.TotalTokenCount
		}
		sDetails = fmt.Sprintf("%-7s • %s tokens %s",
			GreenStyle.Render(fmt.Sprintf("%v", bt.staticRes.Duration.Round(time.Millisecond))),
			BoldWhite.Render(fmt.Sprintf("%d", tokens)),
			MutedStyle.Render("(100% frames pre-ingested)"),
		)
	} else {
		sStatus = badgeRunning
		sDetails = fmt.Sprintf("%-7s • %s",
			CyanStyle.Render(fmt.Sprintf("%v", elapsed)),
			MutedStyle.Render("pre-ingesting full 1-FPS frame timeline..."),
		)
	}

	line1 := fmt.Sprintf("  ⚡ AGENTIC VIDEO  %s  %s", aStatus, aDetails)
	line2 := fmt.Sprintf("  🐢 STATIC (1 FPS) %s  %s", sStatus, sDetails)

	if bt.hasDrawnOnce {
		// Move up 2 lines and clear lines
		fmt.Print("\033[2K\r" + line1 + "\n\033[2K\r" + line2 + "\n\033[2A")
	} else {
		fmt.Println(line1)
		fmt.Println(line2)
		fmt.Print("\033[2A")
		bt.hasDrawnOnce = true
	}

	if isFinal {
		// Move past the 2 lines so subsequent prints don't overwrite
		fmt.Print("\n\n")
	}
}

func (bt *BenchmarkTracker) formatElapsed(d time.Duration) string {
	return FormatElapsed(d)
}

// FormatElapsed formats duration into MM:SS.S for ticker output.
func FormatElapsed(d time.Duration) string {
	d = d.Round(100 * time.Millisecond)
	m := int(d.Minutes())
	s := int(d.Seconds()) % 60
	ms := int(d.Milliseconds()) % 1000 / 100
	return fmt.Sprintf("%02d:%02d.%d", m, s, ms)
}

// MultiModelState stores progress for a specific model during a multi-model shootout.
type MultiModelState struct {
	ModelID  string
	Done     bool
	Result   *runner.Result
	Error    error
	Duration time.Duration
}

// MultiModelTracker tracks live concurrent execution across multiple models simultaneously.
type MultiModelTracker struct {
	isTTY        bool
	startTime    time.Time
	mu           sync.Mutex
	models       []*MultiModelState
	modelMap     map[string]*MultiModelState
	stopChan     chan struct{}
	doneChan     chan struct{}
	hasDrawnOnce bool
}

// NewMultiModelTracker creates a tracker for multi-model concurrent execution.
func NewMultiModelTracker(modelIDs []string) *MultiModelTracker {
	fd := os.Stdout.Fd()
	isTerminal := isatty.IsTerminal(fd) || isatty.IsCygwinTerminal(fd)

	tracker := &MultiModelTracker{
		isTTY:     isTerminal,
		modelMap:  make(map[string]*MultiModelState),
		stopChan:  make(chan struct{}),
		doneChan:  make(chan struct{}),
		startTime: time.Now(),
	}

	for _, mID := range modelIDs {
		state := &MultiModelState{ModelID: mID}
		tracker.models = append(tracker.models, state)
		tracker.modelMap[mID] = state
	}

	return tracker
}

// Start initiates the live 100ms multi-model terminal tracker.
func (mt *MultiModelTracker) Start() {
	mt.startTime = time.Now()

	fmt.Println(SectionHeader.Render("🏎️  MULTI-MODEL AGENTIC VIDEO SHOOTOUT (Parallel Goroutines)"))
	if !mt.isTTY {
		fmt.Printf("[%s] %d models dispatched concurrently in parallel goroutines...\n", mt.formatElapsed(0), len(mt.models))
		return
	}

	go func() {
		defer close(mt.doneChan)
		ticker := time.NewTicker(100 * time.Millisecond)
		defer ticker.Stop()

		for {
			select {
			case <-mt.stopChan:
				mt.redraw(true)
				return
			case <-ticker.C:
				mt.redraw(false)
			}
		}
	}()
}

// Update records completion or error for a specific model.
func (mt *MultiModelTracker) Update(modelID string, done bool, res *runner.Result, err error) {
	mt.mu.Lock()
	defer mt.mu.Unlock()

	state, ok := mt.modelMap[modelID]
	if !ok {
		return
	}

	if done && !state.Done {
		state.Done = true
		state.Result = res
		state.Error = err
		if res != nil {
			state.Duration = res.Duration
		}

		if !mt.isTTY {
			tokStr := "0"
			if res != nil && res.Usage != nil {
				tokStr = fmt.Sprintf("%d", res.Usage.TotalTokenCount)
			}
			if err != nil {
				fmt.Printf("[%s] ❌ %s FAILED: %v\n", mt.formatElapsed(time.Since(mt.startTime)), modelID, err)
			} else {
				fmt.Printf("[%s] ✅ %s COMPLETED in %v (Tokens: %s)\n",
					mt.formatElapsed(time.Since(mt.startTime)),
					modelID,
					res.Duration.Round(time.Millisecond),
					tokStr)
			}
		}
	}
}

// Stop terminates the ticker loop.
func (mt *MultiModelTracker) Stop() {
	if !mt.isTTY {
		return
	}
	close(mt.stopChan)
	<-mt.doneChan
	fmt.Println()
}

func (mt *MultiModelTracker) redraw(isFinal bool) {
	mt.mu.Lock()
	defer mt.mu.Unlock()

	elapsed := time.Since(mt.startTime).Round(100 * time.Millisecond)
	numLines := len(mt.models)
	if numLines == 0 {
		return
	}

	var outputLines []string
	for _, m := range mt.models {
		var status, details string
		if m.Error != nil {
			status = badgeFailed
			details = MutedStyle.Render(fmt.Sprintf("Error: %v", m.Error))
		} else if m.Done && m.Result != nil {
			status = badgeCompleted
			tokens := int32(0)
			if m.Result.Usage != nil {
				tokens = m.Result.Usage.TotalTokenCount
			}
			details = fmt.Sprintf("%-7s • %s tokens %s",
				GreenStyle.Render(fmt.Sprintf("%v", m.Duration.Round(time.Millisecond))),
				BoldWhite.Render(fmt.Sprintf("%d", tokens)),
				MutedStyle.Render("(dynamic frame inspection)"),
			)
		} else {
			status = badgeRunning
			details = fmt.Sprintf("%-7s • %s",
				CyanStyle.Render(fmt.Sprintf("%v", elapsed)),
				MutedStyle.Render("seeking & inspecting timeline chunks..."),
			)
		}

		icon := "🔷"
		if strings.Contains(m.ModelID, "3.8") {
			icon = "🚀"
		} else if strings.Contains(m.ModelID, "3.7") {
			icon = "⚡"
		}

		line := fmt.Sprintf("  %s %-18s %s  %s", icon, m.ModelID, status, details)
		outputLines = append(outputLines, line)
	}

	if mt.hasDrawnOnce {
		for i, line := range outputLines {
			if i == 0 {
				fmt.Print("\033[2K\r" + line + "\n")
			} else {
				fmt.Print("\033[2K\r" + line + "\n")
			}
		}
		fmt.Printf("\033[%dA", numLines)
	} else {
		for _, line := range outputLines {
			fmt.Println(line)
		}
		fmt.Printf("\033[%dA", numLines)
		mt.hasDrawnOnce = true
	}

	if isFinal {
		for i := 0; i < numLines; i++ {
			fmt.Println()
		}
		fmt.Println()
	}
}

func (mt *MultiModelTracker) formatElapsed(d time.Duration) string {
	return FormatElapsed(d)
}
