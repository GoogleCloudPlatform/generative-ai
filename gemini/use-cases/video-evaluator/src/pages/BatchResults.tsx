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

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, ArrowLeft, RotateCcw, Wrench } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BatchVideoList } from '@/components/BatchVideoList';
import { CoverageGauge } from '@/components/CoverageGauge';
import { CoverageSummary } from '@/components/CoverageSummary';
import { PromptSuggestionsPanel } from '@/components/PromptSuggestions';
import { IssueList } from '@/components/IssueList';
import { VideoPlayer } from '@/components/VideoPlayer';
import { Timeline } from '@/components/Timeline';
import { RemediationOptions } from '@/components/RemediationOptions';
import { RegeneratedResults } from '@/components/RegeneratedResults';
import { useVideoRegeneration } from '@/hooks/useVideoRegeneration';
import { BatchEvaluation } from '@/lib/batch-types';
import { VeoModelKey } from '@/lib/veo';
import { Flag } from '@/lib/types';

interface BatchResultsProps {
  batch: BatchEvaluation;
  onReset: () => void;
}

const BatchResultsPage = ({ batch, onReset }: BatchResultsProps) => {
  const navigate = useNavigate();
  const [selectedVideoId, setSelectedVideoId] = useState<string>(batch.videos[0]?.id ?? '');
  const [currentTime, setCurrentTime] = useState(0);
  const [selectedFlagId, setSelectedFlagId] = useState<string>();
  const [showRemediation, setShowRemediation] = useState(false);
  
  const { regeneration, regenerate, resetRegeneration } = useVideoRegeneration();

  const selectedVideo = batch.videos.find(v => v.id === selectedVideoId);

  // Aggregate unmatched issues across all videos
  const allUnmatched = batch.videos.flatMap(v => v.unmatchedIssues);

  const handleFlagClick = (flag: Flag) => {
    setSelectedFlagId(flag.id);
    setCurrentTime(flag.timestampSeconds);
  };

  const handleRegenerate = (options: {
    prompt: string;
    model: VeoModelKey;
    durationSeconds: number;
    aspectRatio: '16:9' | '9:16' | '1:1';
    includeAudio: boolean;
    strategy: 'creative' | 'similarity';
    originalVideoUrl?: string;
  }) => {
    if (!selectedVideo) return;
    regenerate(selectedVideo.name, selectedVideo.duration, options);
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container flex items-center justify-between h-14 px-4">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => navigate('/')}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <Shield className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-bold tracking-tight text-foreground">{batch.name}</h1>
          </div>
          <Button variant="ghost" size="sm" onClick={onReset}>
            <RotateCcw className="h-3.5 w-3.5 mr-2" /> New Batch
          </Button>
        </div>
      </header>

      <main className="container px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr_280px] gap-6">
          {/* Left sidebar: video list */}
          <div className="space-y-4">
            <div className="flex justify-center">
              <CoverageGauge
                coverage={batch.overallCoverage}
                threshold={batch.coverageThreshold}
              />
            </div>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground">
                  Videos ({batch.videos.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <BatchVideoList
                  videos={batch.videos}
                  selectedVideoId={selectedVideoId}
                  onSelect={id => { setSelectedVideoId(id); setShowRemediation(false); }}
                />
              </CardContent>
            </Card>
          </div>

          {/* Center: video detail */}
          <div className="space-y-4">
            {selectedVideo ? (
              <>
                <VideoPlayer
                  videoUrl={selectedVideo.videoUrl}
                  currentTime={currentTime}
                  onTimeUpdate={setCurrentTime}
                />

                {selectedVideo.detectedFlags.length > 0 && (
                  <Timeline
                    flags={selectedVideo.detectedFlags}
                    duration={selectedVideo.duration}
                    currentTime={currentTime}
                    selectedFlagId={selectedFlagId}
                    onFlagClick={handleFlagClick}
                    onSeek={setCurrentTime}
                  />
                )}

                {!showRemediation ? (
                  <>
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-medium text-foreground">
                        Detected Issues ({selectedVideo.detectedFlags.length})
                      </h3>
                      {selectedVideo.detectedFlags.length > 0 && (
                        <Button size="sm" variant="outline" onClick={() => setShowRemediation(true)}>
                          <Wrench className="h-3.5 w-3.5 mr-1.5" /> Fix Issues
                        </Button>
                      )}
                    </div>

                    <IssueList
                      flags={selectedVideo.detectedFlags}
                      selectedFlagId={selectedFlagId}
                      onFlagClick={handleFlagClick}
                      onConfirm={() => {}}
                      onDismiss={() => {}}
                    />
                  </>
                ) : (
                  <>
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-medium text-foreground">Remediation</h3>
                      <Button size="sm" variant="ghost" onClick={() => setShowRemediation(false)}>
                        Back to Issues
                      </Button>
                    </div>
                    <RemediationOptions
                      video={selectedVideo}
                      onCut={() => {/* TODO: FFmpeg integration */}}
                      onRegenerate={handleRegenerate}
                      isRegenerating={regeneration.status === 'generating' || regeneration.status === 'evaluating'}
                      regenerationStatus={regeneration.statusMessage}
                    />

                    {(regeneration.status === 'generating' || regeneration.status === 'evaluating' || regeneration.status === 'error' || regeneration.status === 'complete') && (
                      <div className="mt-4">
                        <RegeneratedResults
                          regeneration={regeneration}
                          originalScore={selectedVideo.coverage * 100} // Mapping coverage to score
                          originalFlagCount={selectedVideo.detectedFlags.length}
                        />
                      </div>
                    )}
                  </>
                )}
              </>
            ) : (
              <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
                Select a video to view results
              </div>
            )}
          </div>

          {/* Right sidebar: coverage + suggestions */}
          <div className="space-y-4 hidden lg:block">
            {selectedVideo && (
              <>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground">
                      Video Coverage
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex justify-center mb-3">
                      <CoverageGauge
                        coverage={selectedVideo.coverage}
                        threshold={batch.coverageThreshold}
                        size="sm"
                      />
                    </div>
                    <CoverageSummary video={selectedVideo} />
                  </CardContent>
                </Card>
              </>
            )}

            {allUnmatched.length > 0 && (
              <PromptSuggestionsPanel unmatchedIssues={allUnmatched} />
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default BatchResultsPage;
