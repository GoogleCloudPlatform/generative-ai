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
import { Plus, X, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { GroundTruthIssue } from '@/lib/batch-types';

interface GroundTruthEditorProps {
  issues: GroundTruthIssue[];
  onAdd: (description: string, startTime: number, endTime?: number) => void;
  onRemove: (issueId: string) => void;
  disabled?: boolean;
}

export function GroundTruthEditor({ issues, onAdd, onRemove, disabled }: GroundTruthEditorProps) {
  const [description, setDescription] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');

  const parseTime = (val: string): number => {
    const parts = val.split(':').map(Number);
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    if (parts.length === 1) return parts[0];
    return 0;
  };

  const handleAdd = () => {
    if (!description.trim() || !startTime.trim()) return;
    const start = parseTime(startTime);
    const end = endTime.trim() ? parseTime(endTime) : undefined;
    onAdd(description.trim(), start, end);
    setDescription('');
    setStartTime('');
    setEndTime('');
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
        <Clock className="h-3 w-3" />
        Known Issues ({issues.length})
      </div>

      {/* Existing issues */}
      {issues.map(issue => (
        <div
          key={issue.id}
          className="flex items-start gap-2 rounded-md bg-muted/50 p-2.5 text-sm group"
        >
          <div className="flex-1 min-w-0">
            <p className="text-foreground">{issue.description}</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {formatSeconds(issue.startTime)}
              {issue.endTime ? ` – ${formatSeconds(issue.endTime)}` : ''}
            </p>
          </div>
          {!disabled && (
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={() => onRemove(issue.id)}
            >
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>
      ))}

      {/* Add new issue */}
      {!disabled && (
        <div className="space-y-2 rounded-md border border-dashed border-border p-3">
          <Textarea
            placeholder="Describe the problem (e.g., 'Hand has 6 fingers')"
            value={description}
            onChange={e => setDescription(e.target.value)}
            className="min-h-[60px] text-sm"
          />
          <div className="flex items-center gap-2">
            <Input
              placeholder="Start (0:05)"
              value={startTime}
              onChange={e => setStartTime(e.target.value)}
              className="w-24 text-xs"
            />
            <span className="text-muted-foreground text-xs">–</span>
            <Input
              placeholder="End (opt)"
              value={endTime}
              onChange={e => setEndTime(e.target.value)}
              className="w-24 text-xs"
            />
            <Button size="sm" variant="secondary" onClick={handleAdd} disabled={!description.trim() || !startTime.trim()}>
              <Plus className="h-3 w-3 mr-1" /> Add
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function formatSeconds(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

