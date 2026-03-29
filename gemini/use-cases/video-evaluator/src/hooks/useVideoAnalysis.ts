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

import { useState, useCallback, useRef } from 'react';
import { AnalysisResult, AgentConfig, AgentResult, Flag } from '@/lib/types';
import { extractFrames } from '@/lib/video-utils';
import { runAgent, computeCoherenceScore } from '@/lib/gemini';
import { getStoredAgentConfigs, saveAgentConfigs } from '@/lib/agent-storage';

interface UseVideoAnalysisReturn {
  isAnalyzing: boolean;
  progress: number;
  frameExtractionProgress: number;
  agentResults: AgentResult[];
  result: AnalysisResult | null;
  error: string | null;
  agentConfigs: AgentConfig[];
  setAgentConfigs: (configs: AgentConfig[]) => void;
  analyzeVideo: (file: File, originPrompt?: string) => Promise<void>;
  reset: () => void;
  updateFlag: (flagId: string, update: Partial<Flag>) => void;
}

export function useVideoAnalysis(): UseVideoAnalysisReturn {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [frameExtractionProgress, setFrameExtractionProgress] = useState(0);
  const [agentResults, setAgentResults] = useState<AgentResult[]>([]);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [agentConfigs, setAgentConfigsState] = useState<AgentConfig[]>(getStoredAgentConfigs());

  const setAgentConfigs = useCallback((next: AgentConfig[]) => {
    setAgentConfigsState(next);
    saveAgentConfigs(next);
  }, []);

  const reset = useCallback(() => {
    setIsAnalyzing(false);
    setProgress(0);
    setFrameExtractionProgress(0);
    setAgentResults([]);
    setResult(null);
    setError(null);
  }, []);

  const updateFlag = useCallback((flagId: string, update: Partial<Flag>) => {
    setResult(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        flags: prev.flags.map(f => f.id === flagId ? { ...f, ...update } : f),
      };
    });
  }, []);

  const analyzeVideo = useCallback(async (file: File, originPrompt?: string) => {
    setIsAnalyzing(true);
    setError(null);
    setProgress(0);
    setFrameExtractionProgress(0);

    const enabledAgents = agentConfigs.filter(a => a.enabled);
    
    // Initialize agent results
    const initialResults: AgentResult[] = enabledAgents.map(a => ({
      agent: a.type,
      flags: [],
      status: 'pending',
    }));
    setAgentResults(initialResults);

    try {
      // Step 1: Extract frames or image
      setProgress(10);
      let frames: string[] = [];
      let duration = 0;

      if (file.type.startsWith('image/')) {
        const { fileToBase64 } = await import('@/lib/video-utils');
        const base64 = await fileToBase64(file);
        frames = [base64];
        setFrameExtractionProgress(100);
        setProgress(30);
      } else {
        const result = await extractFrames(file, 12, (p) => {
          setFrameExtractionProgress(p);
          setProgress(10 + (p / 100) * 20);
        });
        frames = result.frames;
        duration = result.duration;
      }

      if (frames.length === 0) {
        throw new Error('No frames could be extracted from the video');
      }

      // Step 2: Run agents in parallel
      setProgress(30);
      const videoUrl = URL.createObjectURL(file);

      // Update all to running
      setAgentResults(prev => prev.map(r => ({ ...r, status: 'running' as const })));

      const agentPromises = enabledAgents.map(async (config, idx) => {
        try {
          const flags = await runAgent(config, frames, duration);
          const agentResult: AgentResult = { agent: config.type, flags, status: 'complete' };
          setAgentResults(prev => prev.map(r => r.agent === config.type ? agentResult : r));
          setProgress(30 + ((idx + 1) / enabledAgents.length) * 60);
          return agentResult;
        } catch (e) {
          const agentResult: AgentResult = {
            agent: config.type,
            flags: [],
            status: 'error',
            error: e instanceof Error ? e.message : 'Unknown error',
          };
          setAgentResults(prev => prev.map(r => r.agent === config.type ? agentResult : r));
          return agentResult;
        }
      });

      const results = await Promise.all(agentPromises);
      const allFlags = results.flatMap(r => r.flags).sort((a, b) => a.timestampSeconds - b.timestampSeconds);
      const coherenceScore = computeCoherenceScore(allFlags);

      // Check if all agents failed
      const errorCount = results.filter(r => r.status === 'error').length;
      if (errorCount > 0 && errorCount === enabledAgents.length) {
        throw new Error('All evaluation agents failed to complete. Please check your API key and connection.');
      }

      setProgress(100);
      setResult({
        id: Date.now().toString(),
        videoName: file.name,
        videoUrl,
        videoDuration: duration,
        createdAt: new Date(),
        coherenceScore,
        agents: results,
        flags: allFlags,
        originPrompt,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed');
    } finally {
      setIsAnalyzing(false);
    }
  }, [agentConfigs]);

  return {
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
  };
}
