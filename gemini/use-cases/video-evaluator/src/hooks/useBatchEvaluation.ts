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
import { AgentConfig, AnalysisResult, Flag } from '@/lib/types';
import { extractFrames, fileToBase64 } from '@/lib/video-utils';
import { runAgent, computeCoherenceScore } from '@/lib/gemini';
import { generateVideoWithVeo } from '@/lib/veo';

// We need a helper from Gemini to analyze trends
import { getStoredApiKey, getStoredModel } from '@/lib/gemini-config';
import { GoogleGenerativeAI } from '@google/generative-ai';

export interface BatchItem {
  id: string;
  file: File;
  originalResult: AnalysisResult | null;
  regeneratedResult: AnalysisResult | null;
  status: 'pending' | 'analyzing' | 'remediating' | 'regenerating' | 'done' | 'error';
  error?: string;
}

export function useBatchEvaluation() {
  const [items, setItems] = useState<BatchItem[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [globalFixPrompt, setGlobalFixPrompt] = useState<string | null>(null);
  const [batchInsights, setBatchInsights] = useState<string | null>(null);

  const addFiles = useCallback((files: File[]) => {
    const newItems = files.map(f => ({
      id: Math.random().toString(36).substring(7),
      file: f,
      originalResult: null,
      regeneratedResult: null,
      status: 'pending' as const,
    }));
    setItems(prev => [...prev, ...newItems]);
  }, []);

  const clearBatch = useCallback(() => setItems([]), []);

  // Helper to process a single file end-to-end for analysis
  const analyzeSingleFile = async (file: File, configs: AgentConfig[]): Promise<AnalysisResult> => {
    let frames: string[] = [];
    let duration = 0;
    
    if (file.type.startsWith('image/')) {
      frames = [await fileToBase64(file)];
    } else {
      const res = await extractFrames(file, 12);
      frames = res.frames;
      duration = res.duration;
    }

    const enabledAgents = configs.filter(c => c.enabled);
    const agentPromises = enabledAgents.map(async (config) => {
      try {
        const flags = await runAgent(config, frames, duration);
        return { agent: config.type, flags, status: 'complete' as const };
      } catch (e) {
        return { agent: config.type, flags: [], status: 'error' as const, error: String(e) };
      }
    });

    const results = await Promise.all(agentPromises);
    const allFlags = results.flatMap(r => r.flags).sort((a, b) => a.timestampSeconds - b.timestampSeconds);
    
    return {
      id: Date.now().toString(),
      videoName: file.name,
      videoUrl: URL.createObjectURL(file), // Will be revoked eventually, but fine for session
      videoDuration: duration,
      createdAt: new Date(),
      coherenceScore: computeCoherenceScore(allFlags),
      agents: results,
      flags: allFlags,
    };
  };

  const startBatchAnalysis = useCallback(async (configs: AgentConfig[]) => {
    setIsProcessing(true);
    setGlobalFixPrompt(null);

    // Analyze all items in parallel (or sequentially if too heavy, but parallel is faster)
    const updatedItems = await Promise.all(items.map(async (item) => {
      if (item.status !== 'pending' && item.originalResult) return item;

      // Mark running
      setItems(prev => prev.map(i => i.id === item.id ? { ...i, status: 'analyzing' } : i));

      try {
        const result = await analyzeSingleFile(item.file, configs);
        return { ...item, originalResult: result, status: 'done' as const };
      } catch (e) {
        return { ...item, status: 'error' as const, error: String(e) };
      }
    }));

    setItems(updatedItems);
    setIsProcessing(false);
  }, [items]);

  const generateBatchInsights = useCallback(async () => {
    const allIssues = items
      .filter(i => i.originalResult)
      .flatMap(i => i.originalResult!.flags.map(f => `Video ${i.file.name}: [${f.severity}] ${f.description}`));

    if (allIssues.length === 0) return null;

    setIsProcessing(true);
    try {
      const ai = new GoogleGenerativeAI(getStoredApiKey()!);
      const model = ai.getGenerativeModel({ model: getStoredModel() });
      
      const prompt = `You are an expert AI Prompt Engineer and Video Director Analyst.
      A user has generated a batch of AI videos that share several reality-check flaws.
      Here are the critical issues detected across their batch:
      ${allIssues.join('\n')}
      
      Write a clear, encouraging "Prompt Engineering Insights Report" (in plain text formatted cleanly with spacing) summarizing:
      1. What specific concepts the user's current prompts are struggling with across the board.
      2. Specific, actionable advice on how they should alter their text-to-video prompts to prevent these issues.
      3. Recommend any positive reinforcement keywords to add to their future prompts.
      Keep it readable and to the point. No markdown bolding, just well spaced paragraphs.`;

      const res = await model.generateContent(prompt);
      const report = res.response.text().trim();
      setBatchInsights(report);
      return report;
    } catch (e) {
      console.error(e);
      return null;
    } finally {
      setIsProcessing(false);
    }
  }, [items]);

  const generateSweepingFix = useCallback(async () => {
    // Collect all flags across all videos
    const allIssues = items
      .filter(i => i.originalResult)
      .flatMap(i => i.originalResult!.flags.map(f => `Video ${i.file.name}: [${f.severity}] ${f.description}`));

    if (allIssues.length === 0) return null;

    setIsProcessing(true);
    try {
      const ai = new GoogleGenerativeAI(getStoredApiKey()!);
      const model = ai.getGenerativeModel({ model: getStoredModel() });
      
      const prompt = `You are a universal Prompt Architect. 
      I have a batch of AI-generated videos that all share common severe flaws.
      Here are the critical issues detected across the batch:
      ${allIssues.join('\n')}
      
      Identify the overarching trend (e.g. "always messes up hands", "lighting is flat").
      Provide a single, powerful "Negative Prompt" or "Positive Guidance" instruction (max 1-2 sentences) that we can append to ALL video generation requests to fix this across the board natively in Veo. DO NOT wrap the output in quotes. Just output the raw instruction.`;

      const res = await model.generateContent(prompt);
      const fix = res.response.text().trim();
      setGlobalFixPrompt(fix);
      return fix;
    } catch (e) {
      console.error(e);
      return null;
    } finally {
      setIsProcessing(false);
    }
  }, [items]);

  const startBatchRegeneration = useCallback(async (universalFix: string) => {
    setIsProcessing(true);

    const updatedItems = await Promise.all(items.map(async (item) => {
      if (!item.originalResult) return item;
      
      setItems(prev => prev.map(i => i.id === item.id ? { ...i, status: 'regenerating' } : i));

      try {
        // Find reference images for similarity
        let referenceImages: string[] = [];
        if (item.file.type.startsWith('video/')) {
           const extracted = await extractFrames(item.file, 3); // start, mid, end
           referenceImages = extracted.frames;
        } else {
           referenceImages = [await fileToBase64(item.file)];
        }

        const prompt = `A cinematic shot. REMEDIATION GUIDANCE: ${universalFix}`;
        
        // Use Veo model directly (poll via Veo API)
        const videoPoller = await generateVideoWithVeo({
          model: 'veo-3.1',
          prompt,
          aspectRatio: '16:9',
          durationSeconds: 5,
          referenceImages,
          strategy: 'similarity',
          onStatusUpdate: () => {},
        });

        // The poller takes 2-5 minutes per video
        const generatedVideos = await videoPoller;
        if (!generatedVideos || generatedVideos.length === 0) throw new Error("No video returned");

        const newVideoData = generatedVideos[0];
        
        // Once regenerated, we must run the analysis again!
        setItems(prev => prev.map(i => i.id === item.id ? { ...i, status: 'analyzing' } : i));
        
        // Convert base64 video string into a File object so we can evaluate it
        const res = await fetch(`data:video/mp4;base64,${newVideoData}`);
        const blob = await res.blob();
        const newFile = new File([blob], `regenerated_${item.file.name}.mp4`, { type: 'video/mp4' });

        // Retrieve existing configs since we don't have them in scope (or just mock them if simple)
        const configsString = localStorage.getItem('reality-check-configs');
        const configs: AgentConfig[] = configsString ? JSON.parse(configsString) : [];

        const newResult = await analyzeSingleFile(newFile, configs);

        return { ...item, regeneratedResult: newResult, status: 'done' as const };
      } catch (e) {
        return { ...item, status: 'error' as const, error: String(e) };
      }
    }));

    setItems(updatedItems);
    setIsProcessing(false);
  }, [items]);

  return {
    items,
    isProcessing,
    globalFixPrompt,
    batchInsights,
    addFiles,
    clearBatch,
    startBatchAnalysis,
    generateSweepingFix,
    generateBatchInsights,
    startBatchRegeneration
  };
}
