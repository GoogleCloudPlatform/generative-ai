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
import { Flag, AgentResult, AnalysisResult } from '@/lib/types';
import { runAgent, computeCoherenceScore } from '@/lib/gemini';
import { getStoredAgentConfigs } from '@/lib/agent-storage';
import { generateVideoWithVeo, VeoModelKey } from '@/lib/veo';
import { extractFrames, extractSpecificFrames } from '@/lib/video-utils';

export interface VideoVersion {
  id: string;
  videoUrl: string;
  prompt: string;
  reEvaluation: AnalysisResult | null;
  timestamp: Date;
}

export interface RegenerationResult {
  versions: VideoVersion[];
  status: 'idle' | 'generating' | 'evaluating' | 'complete' | 'error';
  statusMessage: string;
  generatedVideoUrl?: string; // Add this
  error?: string;
}

export function useVideoRegeneration() {
  const [regeneration, setRegeneration] = useState<RegenerationResult>({
    versions: [],
    status: 'idle',
    statusMessage: '',
  });

  const regenerate = useCallback(async (
    videoName: string,
    originalDuration: number,
    options: {
      prompt: string;
      model: VeoModelKey;
      durationSeconds: number;
      aspectRatio: '16:9' | '9:16' | '1:1';
      includeAudio: boolean;
      inputImageBase64?: string;
      strategy?: 'creative' | 'similarity';
      originalVideoUrl?: string;
    }
  ) => {
    const { prompt, model, durationSeconds, aspectRatio, includeAudio, inputImageBase64, strategy = 'creative', originalVideoUrl } = options;
    setRegeneration(prev => ({
      ...prev,
      status: 'generating',
      statusMessage: 'Preparing regeneration...',
    }));

    try {
      let referenceImages: string[] | undefined;

      // Extract reference frames if similarity strategy is chosen
      if (strategy === 'similarity' && originalVideoUrl) {
        setRegeneration(prev => ({ ...prev, statusMessage: 'Extracting reference frames from original video...' }));
        try {
          const response = await fetch(originalVideoUrl);
          const blob = await response.blob();
          const file = new File([blob], 'reference.mp4', { type: 'video/mp4' });
          
          // Extract specific frames: First, Middle, and near-End frames (Up to 3 for Veo 3.x)
          const timestamps = [0, originalDuration / 2, Math.max(0, originalDuration - 0.5)];
          const { frames } = await extractSpecificFrames(file, timestamps);
          referenceImages = frames;
        } catch (err) {
          console.warn('Failed to extract reference frames, falling back to creative mode:', err);
        }
      }

      // Generate video with Veo
      const { videoUrl } = await generateVideoWithVeo({
        prompt,
        model,
        aspectRatio,
        durationSeconds,
        includeAudio,
        inputImageBase64,
        referenceImages,
        onStatusUpdate: (statusMessage) => {
          setRegeneration(prev => ({ ...prev, statusMessage }));
        },
      });

      setRegeneration(prev => ({
        ...prev,
        status: 'evaluating',
        statusMessage: 'Re-evaluating generated video with agents...',
        generatedVideoUrl: videoUrl, // Store the URL for preview
      }));

      // Re-evaluate the generated video
      const reEvalResult = await reEvaluateVideo(videoUrl, videoName, durationSeconds);

      const newVersion: VideoVersion = {
        id: `v${regeneration.versions.length + 1}-${Date.now()}`,
        videoUrl,
        prompt,
        reEvaluation: reEvalResult,
        timestamp: new Date(),
      };

      setRegeneration(prev => ({
        versions: [...prev.versions, newVersion],
        status: 'complete',
        statusMessage: 'Complete',
        generatedVideoUrl: videoUrl,
      }));
    } catch (e) {
      console.error('Regeneration failed:', e);
      setRegeneration(prev => ({
        ...prev,
        status: 'error',
        statusMessage: '',
        error: e instanceof Error ? e.message : 'Regeneration failed',
      }));
    }
  }, []);

  const resetRegeneration = useCallback(() => {
    setRegeneration({
      versions: [],
      status: 'idle',
      statusMessage: '',
    });
  }, []);

  return { regeneration, regenerate, resetRegeneration };
}

/**
 * Re-evaluate a generated video using the same multi-agent pipeline.
 * Creates a blob URL video element, extracts frames, then runs agents.
 */
async function reEvaluateVideo(
  videoUrl: string,
  videoName: string,
  originalDuration: number
): Promise<AnalysisResult> {
  // Fetch the video blob and create a File for frame extraction
  const response = await fetch(videoUrl);
  const blob = await response.blob();
  const file = new File([blob], `${videoName}-regenerated.mp4`, { type: 'video/mp4' });

  // Extract frames from the regenerated video
  const { frames, duration } = await extractFrames(file, 10);

  const enabledAgents = getStoredAgentConfigs().filter(a => a.enabled);

  const agentPromises = enabledAgents.map(async (config): Promise<AgentResult> => {
    try {
      const flags = await runAgent(config, frames, duration);
      return { agent: config.type, flags, status: 'complete' };
    } catch (e) {
      return {
        agent: config.type,
        flags: [],
        status: 'error',
        error: e instanceof Error ? e.message : 'Unknown error',
      };
    }
  });

  const results = await Promise.all(agentPromises);
  const allFlags = results.flatMap(r => r.flags).sort((a, b) => a.timestampSeconds - b.timestampSeconds);
  const coherenceScore = computeCoherenceScore(allFlags);

  return {
    id: `regen-${Date.now()}`,
    videoName: `${videoName} (Regenerated)`,
    videoUrl,
    videoDuration: duration || originalDuration,
    createdAt: new Date(),
    coherenceScore,
    agents: results,
    flags: allFlags,
  };
}
