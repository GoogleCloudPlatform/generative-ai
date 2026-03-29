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
import { Scissors, RefreshCw, Copy, Check, Loader2, Sparkles, Film } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { VideoEntry } from '@/lib/batch-types';
import { recommendStrategy, flagsToSections, generateRegenerationPrompt } from '@/lib/remediation';
import { VEO_MODELS, VeoModelKey } from '@/lib/veo';
import { PromptEditorDialog } from './PromptEditorDialog';
import { cn } from '@/lib/utils';

interface RemediationOptionsProps {
  video: VideoEntry;
  onCut: (sections: { start: number; end: number }[]) => void;
  onRegenerate: (options: {
    prompt: string;
    model: VeoModelKey;
    durationSeconds: number;
    aspectRatio: '16:9' | '9:16' | '1:1';
    includeAudio: boolean;
    strategy: 'creative' | 'similarity';
    originalVideoUrl?: string;
  }) => void;
  isRegenerating?: boolean;
  regenerationStatus?: string;
}

export function RemediationOptions({ video, onCut, onRegenerate, isRegenerating, regenerationStatus }: RemediationOptionsProps) {
  const [generatedPrompt, setGeneratedPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showEditor, setShowEditor] = useState(false);
  const [isPreparingPrompt, setIsPreparingPrompt] = useState(false);
  const [initialPrompt, setInitialPrompt] = useState('');

  const recommended = recommendStrategy(video.detectedFlags, video.duration);
  const sections = flagsToSections(video.detectedFlags);
  const totalCutDuration = sections.reduce((sum, s) => sum + (s.end - s.start), 0);
  const cutPercentage = video.duration > 0 ? Math.round((totalCutDuration / video.duration) * 100) : 0;

  const handleOpenEditor = () => {
    setShowEditor(true);
    // The prompt will be generated inside the dialog or we can trigger it now
    if (!initialPrompt) {
      setIsPreparingPrompt(true);
      generateRegenerationPrompt(video.name, video.detectedFlags, video.duration, video.originPrompt, true)
        .then(setInitialPrompt)
        .finally(() => setIsPreparingPrompt(false));
    }
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(generatedPrompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {/* Cut Option */}
      <Card className={cn(
        'transition-all hover:border-primary/50',
        recommended === 'cut' && 'border-primary/30 bg-primary/5'
      )}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <Scissors className="h-5 w-5 text-primary" />
            {recommended === 'cut' && (
              <span className="text-[10px] font-medium text-primary uppercase tracking-wider">Recommended</span>
            )}
          </div>
          <CardTitle className="text-base">Cut Sections</CardTitle>
          <CardDescription className="text-xs">
            Remove {sections.length} problematic section{sections.length !== 1 ? 's' : ''} ({cutPercentage}% of video)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-1.5 mb-3">
            {sections.map((s, i) => (
              <div key={i} className="flex items-center justify-between text-xs text-muted-foreground bg-muted/50 rounded px-2 py-1">
                <span>{formatSec(s.start)} – {formatSec(s.end)}</span>
                <span>{(s.end - s.start).toFixed(1)}s</span>
              </div>
            ))}
          </div>
          <Button
            size="sm"
            variant={recommended === 'cut' ? 'default' : 'secondary'}
            className="w-full"
            onClick={() => onCut(sections)}
          >
            <Scissors className="h-3.5 w-3.5 mr-1.5" />
            Cut & Download
          </Button>
        </CardContent>
      </Card>

      {/* Regenerate Option */}
      <Card className={cn(
        'transition-all hover:border-primary/50',
        recommended === 'regenerate' && 'border-primary/30 bg-primary/5'
      )}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <Film className="h-5 w-5 text-primary" />
            {recommended === 'regenerate' && (
              <span className="text-[10px] font-medium text-primary uppercase tracking-wider">Recommended</span>
            )}
          </div>
          <CardTitle className="text-base">Advanced Regeneration</CardTitle>
          <CardDescription className="text-xs">
            Generate a new video using Google Veo and re-evaluate automatically
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* Primary action: Regenerate with Veo */}
          <Button
            size="sm"
            variant={recommended === 'regenerate' ? 'default' : 'secondary'}
            className="w-full"
            onClick={handleOpenEditor}
            disabled={isRegenerating || isGenerating || isPreparingPrompt}
          >
            {isRegenerating ? (
              <><Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> {regenerationStatus || 'Regenerating...'}</>
            ) : (
              <><Sparkles className="h-3.5 w-3.5 mr-1.5" /> Configure & Regenerate</>
            )}
          </Button>

          {isRegenerating && regenerationStatus && (
            <p className="text-[10px] text-muted-foreground text-center">{regenerationStatus}</p>
          )}

          {/* Secondary: Generate prompt only */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-card px-2 text-muted-foreground">or just get the prompt</span>
            </div>
          </div>

          {!generatedPrompt ? (
            <Button
              size="sm"
              variant="ghost"
              className="w-full text-xs"
              onClick={handleOpenEditor}
              disabled={isGenerating || isRegenerating || isPreparingPrompt}
            >
              {isPreparingPrompt ? (
                <><Loader2 className="h-3 w-3 mr-1.5 animate-spin" /> Preparing Editor...</>
              ) : (
                <><RefreshCw className="h-3 w-3 mr-1.5" /> Generate Prompt Filter</>
              )}
            </Button>
          ) : (
            <>
              <Textarea
                value={generatedPrompt}
                readOnly
                className="text-xs min-h-[80px] font-mono"
              />
              <Button size="sm" variant="ghost" className="w-full text-xs" onClick={handleCopy}>
                {copied ? <Check className="h-3 w-3 mr-1.5" /> : <Copy className="h-3 w-3 mr-1.5" />}
                {copied ? 'Copied!' : 'Copy Prompt'}
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      <PromptEditorDialog
        open={showEditor}
        onOpenChange={setShowEditor}
        initialPrompt={initialPrompt}
        initialDuration={video.duration}
        onRegenerate={(options) => {
          setShowEditor(false);
          onRegenerate({
            ...options,
            originalVideoUrl: video.videoUrl
          });
        }}
        isGenerating={isRegenerating || false}
      />
    </div>
  );
}

function formatSec(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
}
