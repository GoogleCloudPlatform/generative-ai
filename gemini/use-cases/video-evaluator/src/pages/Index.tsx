// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useVideoAnalysis } from '@/hooks/useVideoAnalysis';
import { useVideoRegeneration } from '@/hooks/useVideoRegeneration';
import { VideoDropzone } from '@/components/VideoDropzone';
import { ProcessingQueue } from '@/components/ProcessingQueue';
import { AgentSettings } from '@/components/AgentSettings';
import { CoherenceScore } from '@/components/CoherenceScore';
import { VideoPlayer } from '@/components/VideoPlayer';
import { Timeline } from '@/components/Timeline';
import { IssueList } from '@/components/IssueList';
import { MetadataPanel } from '@/components/MetadataPanel';
import { RemediationOptions } from '@/components/RemediationOptions';
import { RegeneratedResults } from '@/components/RegeneratedResults';
import { VersionHistory } from '@/components/VersionHistory';
import { Flag } from '@/lib/types';
import { VideoEntry } from '@/lib/batch-types';
import { VeoModelKey } from '@/lib/veo';
import { Shield, RotateCcw, Settings, Layers, Film, Wrench, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ApiKeyDialog } from '@/components/ApiKeyDialog';
import { hasApiKey } from '@/lib/gemini-config';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

const Index = () => {
  const navigate = useNavigate();
  const {
    isAnalyzing,
    progress,
    frameExtractionProgress,
    agentResults,
    result,
    error,
    agentConfigs,
    setAgentConfigs,
    analyzeVideo,
    reset,
    updateFlag,
  } = useVideoAnalysis();

  const { regeneration, regenerate, resetRegeneration } = useVideoRegeneration();

  const [selectedFlagId, setSelectedFlagId] = useState<string>();
  const [currentTime, setCurrentTime] = useState(0);
  const [showApiDialog, setShowApiDialog] = useState(!hasApiKey());
  const [showRemediation, setShowRemediation] = useState(false);
  const [originPrompt, setOriginPrompt] = useState('');
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  const videoEntryFromResult: VideoEntry | null = result ? {
    id: result.id,
    file: new File([], result.videoName),
    name: result.videoName,
    videoUrl: result.videoUrl,
    duration: result.videoDuration,
    groundTruth: [],
    detectedFlags: result.flags,
    agentResults: result.agents,
    coverage: 0,
    unmatchedIssues: [],
    status: 'complete',
    passed: true,
    originPrompt: result.originPrompt, // Pass it through
  } : null;

  const handleFlagClick = useCallback((flag: Flag) => {
    setSelectedFlagId(flag.id);
    setCurrentTime(flag.timestampSeconds);
  }, []);

  const handleConfirm = useCallback((id: string) => updateFlag(id, { confirmed: true, dismissed: false }), [updateFlag]);
  const handleDismiss = useCallback((id: string) => updateFlag(id, { dismissed: true, confirmed: false }), [updateFlag]);

  const handleRegenerate = useCallback((options: {
    prompt: string;
    model: VeoModelKey;
    durationSeconds: number;
    aspectRatio: '16:9' | '9:16' | '1:1';
    includeAudio: boolean;
    strategy: 'creative' | 'similarity';
    originalVideoUrl?: string;
  }) => {
    if (!result) return;
    regenerate(result.videoName, result.videoDuration, options);
  }, [result, regenerate]);

  const handleReset = useCallback(() => {
    reset();
    resetRegeneration();
    setShowRemediation(false);
  }, [reset, resetRegeneration]);

  return (
    <div className="min-h-screen bg-background">
      <ApiKeyDialog open={showApiDialog} onOpenChange={setShowApiDialog} onSave={() => {}} />
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container flex items-center justify-between h-14 px-4">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-bold tracking-tight text-foreground uppercase">Generative AI</h1>
            <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest ml-1">Video Evaluator</span>
          </div>
          <div className="flex items-center gap-2">
            {result && (
              <Button variant="ghost" size="sm" onClick={handleReset}>
                <RotateCcw className="mr-2 h-3.5 w-3.5" /> New Analysis
              </Button>
            )}
            <Button variant="ghost" size="icon" onClick={() => setShowApiDialog(true)} title="API Settings">
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="container px-4 py-6">
        {!result ? (
          <div className="max-w-3xl mx-auto space-y-6">
            <div className="text-center space-y-2 mb-8">
              <h2 className="text-2xl font-bold text-foreground">AI-Generated Video Quality Analysis</h2>
              <p className="text-muted-foreground max-w-lg mx-auto">
                Multi-agent evaluation powered by Google Gemini. Detects object permanence violations,
                physics errors, and temporal inconsistencies.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
              <div className="rounded-lg border-2 border-primary bg-primary/5 p-5 text-center">
                <Film className="h-6 w-6 text-primary mx-auto mb-2" />
                <h3 className="text-sm font-semibold text-foreground">Single Video</h3>
                <p className="text-xs text-muted-foreground mt-1">Quick analysis of one video</p>
              </div>
              <div
                className="rounded-lg border-2 border-border hover:border-primary/50 p-5 text-center cursor-pointer transition-colors"
                onClick={() => navigate('/batch')}
              >
                <Layers className="h-6 w-6 text-muted-foreground mx-auto mb-2" />
                <h3 className="text-sm font-semibold text-foreground">Batch Evaluation</h3>
                <p className="text-xs text-muted-foreground mt-1">Upload multiple videos with ground truth annotations</p>
              </div>
            </div>

            <div className="space-y-4">
              {!pendingFile ? (
                <VideoDropzone onFileSelected={setPendingFile} isAnalyzing={isAnalyzing} />
              ) : (
                <Card className="border-2 border-primary/20 bg-primary/5 p-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="space-y-4">
                    <div className="flex items-center gap-3">
                      <div className="rounded-full bg-primary/10 p-2">
                        <Sparkles className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-foreground">Add Generation Context</h3>
                        <p className="text-xs text-muted-foreground">What prompt did you use to create this video?</p>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Textarea
                        id="origin-prompt"
                        autoFocus
                        placeholder="Paste the prompt used to generate this video... (Optional)"
                        value={originPrompt}
                        onChange={(e) => setOriginPrompt(e.target.value)}
                        className="min-h-[120px] text-sm bg-background/50 focus-visible:ring-primary/30"
                        disabled={isAnalyzing}
                      />
                      <p className="text-[10px] text-muted-foreground italic">
                        Providing the original prompt helps the AI suggest much better fixes if issues are detected.
                      </p>
                    </div>

                    <div className="flex items-center gap-2 pt-2">
                      <Button 
                        className="flex-1" 
                        onClick={() => {
                          analyzeVideo(pendingFile, originPrompt);
                          setPendingFile(null);
                        }}
                        disabled={isAnalyzing}
                      >
                        {originPrompt.trim() ? 'Analyze with Prompt' : 'Skip & Analyze'}
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => {
                          setPendingFile(null);
                          setOriginPrompt('');
                        }}
                        disabled={isAnalyzing}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                </Card>
              )}
            </div>

            {error && (
              <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">{error}</div>
            )}

            <ProcessingQueue agentResults={agentResults} isAnalyzing={isAnalyzing} frameProgress={frameExtractionProgress} />
            <AgentSettings configs={agentConfigs} onChange={setAgentConfigs} disabled={isAnalyzing} />
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
            <div className="space-y-4">
              <VideoPlayer videoUrl={result.videoUrl} currentTime={currentTime} onTimeUpdate={setCurrentTime} />
              <Timeline
                flags={result.flags}
                duration={result.videoDuration}
                currentTime={currentTime}
                selectedFlagId={selectedFlagId}
                onFlagClick={handleFlagClick}
                onSeek={setCurrentTime}
              />

              <div className="lg:hidden">
                <div className="flex items-center justify-center mb-4">
                  <CoherenceScore score={result.coherenceScore} />
                </div>
              </div>

              {!showRemediation ? (
                <>
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-medium text-foreground">Detected Issues ({result.flags.length})</h3>
                    {result.flags.length > 0 && (
                      <Button size="sm" variant="outline" onClick={() => setShowRemediation(true)}>
                        <Wrench className="h-3.5 w-3.5 mr-1.5" /> Fix Issues
                      </Button>
                    )}
                  </div>
                  <IssueList
                    flags={result.flags}
                    selectedFlagId={selectedFlagId}
                    onFlagClick={handleFlagClick}
                    onConfirm={handleConfirm}
                    onDismiss={handleDismiss}
                  />

                  {regeneration.versions.length > 0 && (
                    <VersionHistory
                      original={result!}
                      versions={regeneration.versions}
                      onFlagClick={setCurrentTime}
                    />
                  )}
                </>
              ) : (
                <>
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-medium text-foreground">Remediation</h3>
                    <Button size="sm" variant="ghost" onClick={() => { setShowRemediation(false); resetRegeneration(); }}>
                      Back to Issues
                    </Button>
                  </div>
                  {videoEntryFromResult && (
                    <RemediationOptions
                      video={videoEntryFromResult}
                      onCut={() => {}}
                      onRegenerate={handleRegenerate}
                      isRegenerating={regeneration.status === 'generating' || regeneration.status === 'evaluating'}
                      regenerationStatus={regeneration.statusMessage}
                    />
                  )}
                </>
              )}

              {/* Versioned Results — Active Status */}
              {(regeneration.status === 'generating' || regeneration.status === 'evaluating' || regeneration.status === 'error' || regeneration.status === 'complete') && (
                <RegeneratedResults
                  regeneration={regeneration}
                  originalScore={result.coherenceScore}
                  originalFlagCount={result.flags.length}
                />
              )}
            </div>

            <div className="space-y-4 hidden lg:block">
              <div className="flex justify-center">
                <CoherenceScore score={result.coherenceScore} />
              </div>
              <ProcessingQueue agentResults={result.agents} isAnalyzing={false} frameProgress={100} />
              <MetadataPanel result={result} />
              <AgentSettings configs={agentConfigs} onChange={setAgentConfigs} disabled={true} />
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Index;
