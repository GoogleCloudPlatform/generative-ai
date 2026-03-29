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

import { useMemo } from 'react';
import { Flag, AgentType } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

interface TimelineProps {
  flags: Flag[];
  duration: number;
  currentTime: number;
  selectedFlagId?: string;
  onFlagClick: (flag: Flag) => void;
  onSeek: (time: number) => void;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-destructive',
  warning: 'bg-warning',
  info: 'bg-info',
};

const AGENT_ROWS: AgentType[] = ['object_permanence', 'physics_motion', 'temporal_consistency'];
const AGENT_LABELS: Record<AgentType, string> = {
  object_permanence: 'OBJ',
  physics_motion: 'PHY',
  temporal_consistency: 'TMP',
};

const AGENT_COLORS: Record<AgentType, string> = {
  object_permanence: 'text-primary',
  physics_motion: 'text-warning',
  temporal_consistency: 'text-success',
};

export function Timeline({ flags, duration, currentTime, selectedFlagId, onFlagClick, onSeek }: TimelineProps) {
  const flagsByAgent = useMemo(() => {
    const map: Record<AgentType, Flag[]> = {
      object_permanence: [],
      physics_motion: [],
      temporal_consistency: [],
    };
    flags.forEach(f => {
      if (map[f.category]) map[f.category].push(f);
    });
    return map;
  }, [flags]);

  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const pct = x / rect.width;
    onSeek(pct * duration);
  };

  const playheadPosition = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div className="rounded-lg border border-border bg-card p-3 space-y-1">
      {AGENT_ROWS.map(agent => (
        <div key={agent} className="flex items-center gap-2">
          <span className={cn('font-mono text-[10px] w-7 shrink-0', AGENT_COLORS[agent])}>
            {AGENT_LABELS[agent]}
          </span>
          <div
            className="relative flex-1 h-6 rounded bg-secondary/50 cursor-pointer"
            onClick={handleTimelineClick}
          >
            {/* Playhead */}
            <div
              className="absolute top-0 bottom-0 w-px bg-foreground/60 z-10 pointer-events-none"
              style={{ left: `${playheadPosition}%` }}
            />

            {/* Flags */}
            {flagsByAgent[agent].map(flag => {
              const position = duration > 0 ? (flag.timestampSeconds / duration) * 100 : 0;
              return (
                <Tooltip key={flag.id}>
                  <TooltipTrigger asChild>
                    <button
                      onClick={(e) => { e.stopPropagation(); onFlagClick(flag); }}
                      className={cn(
                        'absolute top-1 h-4 w-2 rounded-sm transition-all',
                        SEVERITY_COLORS[flag.severity],
                        flag.id === selectedFlagId && 'ring-2 ring-foreground scale-125',
                        flag.dismissed && 'opacity-30',
                      )}
                      style={{ left: `calc(${position}% - 4px)` }}
                    />
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs">
                    <p className="text-xs font-mono">{flag.timestamp}</p>
                    <p className="text-xs">{flag.description}</p>
                  </TooltipContent>
                </Tooltip>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
