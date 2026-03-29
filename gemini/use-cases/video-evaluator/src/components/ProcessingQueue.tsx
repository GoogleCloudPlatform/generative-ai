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

import { AgentResult, AgentConfig, DEFAULT_AGENT_CONFIGS } from '@/lib/types';
import { CheckCircle, Loader2, AlertCircle, Clock, Eye, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ProcessingQueueProps {
  agentResults: AgentResult[];
  isAnalyzing: boolean;
  frameProgress: number;
}

const AGENT_ICONS: Record<string, React.ReactNode> = {
  object_permanence: <Eye className="h-4 w-4" />,
  physics_motion: <Zap className="h-4 w-4" />,
  temporal_consistency: <Clock className="h-4 w-4" />,
};

const AGENT_LABELS: Record<string, string> = {
  object_permanence: 'Object Permanence',
  physics_motion: 'Physics & Motion',
  temporal_consistency: 'Temporal Consistency',
};

export function ProcessingQueue({ agentResults, isAnalyzing, frameProgress }: ProcessingQueueProps) {
  if (!isAnalyzing && agentResults.length === 0) return null;

  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-3">
      <div className="flex items-center gap-2 text-sm font-medium text-foreground">
        {isAnalyzing && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
        <span>{isAnalyzing ? 'Analyzing...' : 'Analysis Complete'}</span>
      </div>

      {isAnalyzing && frameProgress < 100 && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Extracting frames</span>
            <span className="font-mono">{Math.round(frameProgress)}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all duration-300"
              style={{ width: `${frameProgress}%` }}
            />
          </div>
        </div>
      )}

      <div className="space-y-2">
        {agentResults.map((agent) => (
          <div
            key={agent.agent}
            className={cn(
              'flex items-center gap-3 rounded-md px-3 py-2 text-sm',
              agent.status === 'running' && 'bg-primary/5',
              agent.status === 'complete' && 'bg-success/5',
              agent.status === 'error' && 'bg-destructive/5',
            )}
          >
            <span className={cn(
              agent.status === 'running' && 'text-primary',
              agent.status === 'complete' && 'text-success',
              agent.status === 'error' && 'text-destructive',
              agent.status === 'pending' && 'text-muted-foreground',
            )}>
              {AGENT_ICONS[agent.agent]}
            </span>
            <span className="flex-1 text-foreground">{AGENT_LABELS[agent.agent]}</span>
            {agent.status === 'pending' && (
              <span className="text-xs text-muted-foreground">Waiting</span>
            )}
            {agent.status === 'running' && (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
            )}
            {agent.status === 'complete' && (
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-mono text-muted-foreground">
                  {agent.flags.length} flag{agent.flags.length !== 1 ? 's' : ''}
                </span>
                <CheckCircle className="h-3.5 w-3.5 text-success" />
              </div>
            )}
            {agent.status === 'error' && (
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-destructive">{agent.error || 'Failed'}</span>
                <AlertCircle className="h-3.5 w-3.5 text-destructive" />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
