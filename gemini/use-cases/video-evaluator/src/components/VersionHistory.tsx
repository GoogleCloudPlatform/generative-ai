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
import { AnalysisResult } from '@/lib/types';
import { VideoVersion } from '@/hooks/useVideoRegeneration';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Sparkles, History, ChevronRight, CheckCircle2, XCircle, Film, AlertCircle } from 'lucide-react';
import { IssueList } from './IssueList';
import { CoherenceScore } from './CoherenceScore';
import { cn } from '@/lib/utils';

interface VersionHistoryProps {
  original: AnalysisResult;
  versions: VideoVersion[];
  onFlagClick?: (timestamp: number) => void;
}

export function VersionHistory({ original, versions, onFlagClick }: VersionHistoryProps) {
  const [expandedVersionId, setExpandedVersionId] = useState<string>(
    versions.length > 0 ? versions[versions.length - 1].id : 'original'
  );

  const allVersions = [
    {
      id: 'original',
      name: 'Version 1 (Original)',
      result: original,
      isOriginal: true,
      timestamp: original.createdAt,
    },
    ...versions.map((v, i) => ({
      id: v.id,
      name: `Version ${i + 2}`,
      result: v.reEvaluation!,
      isOriginal: false,
      timestamp: v.timestamp,
      prompt: v.prompt
    }))
  ];

  return (
    <div className="space-y-4 mt-8">
      <div className="flex items-center gap-2 mb-2">
        <History className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Evaluation history</h3>
      </div>

      <Accordion type="single" collapsible value={expandedVersionId} onValueChange={setExpandedVersionId} className="w-full space-y-3 border-none">
        {allVersions.map((v) => (
          <AccordionItem
            key={v.id}
            value={v.id}
            className={cn(
              "border rounded-lg px-4 bg-card/50 transition-all",
              expandedVersionId === v.id ? "border-primary/30 ring-1 ring-primary/10 shadow-sm" : "border-border hover:border-primary/20"
            )}
          >
            <AccordionTrigger className="hover:no-underline py-4">
              <div className="flex items-center justify-between w-full pr-4 text-left">
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "p-1.5 rounded-full",
                    v.isOriginal ? "bg-muted text-muted-foreground" : "bg-primary/10 text-primary"
                  )}>
                    {v.isOriginal ? <Film className="h-3.5 w-3.5" /> : <Sparkles className="h-3.5 w-3.5" />}
                  </div>
                  <div>
                    <h4 className="text-sm font-medium leading-none">{v.name}</h4>
                    <p className="text-[10px] text-muted-foreground mt-1">
                      {new Date(v.timestamp).toLocaleTimeString()} · {v.result.flags.length} issues
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div className="flex flex-col items-end">
                    <span className="text-[10px] uppercase tracking-tighter text-muted-foreground font-medium">Coherence</span>
                    <span className={cn(
                      "text-base font-bold font-mono",
                      v.result.coherenceScore >= 80 ? "text-success" : v.result.coherenceScore >= 50 ? "text-warning" : "text-destructive"
                    )}>
                      {v.result.coherenceScore}
                    </span>
                  </div>
                </div>
              </div>
            </AccordionTrigger>
            <AccordionContent className="pt-0 pb-4">
              <div className="space-y-4 pt-2 border-t border-border/50">
                {/* Video Player */}
                <div className="aspect-video relative rounded-md overflow-hidden bg-black/20 border">
                  <video
                    src={v.result.videoUrl}
                    controls
                    className="w-full h-full object-contain"
                  />
                </div>

                {/* Prompt Info (if not original) */}
                {'prompt' in v && v.prompt && (
                  <div className="bg-muted/50 rounded-lg p-3 text-[11px]">
                    <p className="font-semibold text-muted-foreground mb-1 uppercase tracking-tight">Regeneration Prompt</p>
                    <p className="line-clamp-3 text-foreground italic">"{v.prompt}"</p>
                  </div>
                )}

                {/* Issues List */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h5 className="text-[11px] font-bold uppercase tracking-tight text-muted-foreground">
                      Analysis Details
                    </h5>
                    {v.result.flags.length === 0 ? (
                      <Badge variant="outline" className="text-[10px] bg-success/5 text-success border-success/20">
                        <CheckCircle2 className="h-2.5 w-2.5 mr-1" /> No Issues Detected
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-[10px] bg-destructive/5 text-destructive border-destructive/20">
                        <AlertCircle className="h-2.5 w-2.5 mr-1" /> {v.result.flags.length} Potential Issues
                      </Badge>
                    )}
                  </div>

                  <IssueList
                    flags={v.result.flags}
                    onFlagClick={(flag) => onFlagClick?.(flag.timestampSeconds)}
                    onConfirm={() => {}}
                    onDismiss={() => {}}
                    compact
                  />
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
}
