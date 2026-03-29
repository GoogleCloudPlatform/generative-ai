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

import { Film, X, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { VideoEntry } from '@/lib/batch-types';
import { cn } from '@/lib/utils';

interface BatchVideoListProps {
  videos: VideoEntry[];
  selectedVideoId?: string;
  onSelect: (videoId: string) => void;
  onRemove?: (videoId: string) => void;
  disabled?: boolean;
}

const STATUS_CONFIG: Record<VideoEntry['status'], { icon: any; label: string; className: string }> = {
  pending: { icon: Film, label: 'Pending', className: 'text-muted-foreground' },
  extracting: { icon: Loader2, label: 'Extracting frames...', className: 'text-primary animate-spin' },
  analyzing: { icon: Loader2, label: 'Running agents...', className: 'text-primary animate-spin' },
  matching: { icon: Loader2, label: 'Matching coverage...', className: 'text-primary animate-spin' },
  complete: { icon: CheckCircle2, label: 'Complete', className: 'text-success' },
  error: { icon: AlertCircle, label: 'Error', className: 'text-destructive' },
};

export function BatchVideoList({ videos, selectedVideoId, onSelect, onRemove, disabled }: BatchVideoListProps) {
  return (
    <div className="space-y-1">
      {videos.map(video => {
        const config = STATUS_CONFIG[video.status];
        const Icon = config.icon;
        const isSelected = video.id === selectedVideoId;

        return (
          <div
            key={video.id}
            className={cn(
              'flex items-center gap-3 rounded-md px-3 py-2.5 cursor-pointer transition-colors group',
              isSelected ? 'bg-accent' : 'hover:bg-muted/50'
            )}
            onClick={() => onSelect(video.id)}
          >
            <Icon className={cn('h-4 w-4 shrink-0', config.className)} />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">{video.name}</p>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>{config.label}</span>
                {video.status === 'complete' && (
                  <>
                    <span>·</span>
                    <span className={video.coverage >= 0.85 ? 'text-success' : 'text-warning'}>
                      {Math.round(video.coverage * 100)}% coverage
                    </span>
                  </>
                )}
                {video.groundTruth.length > 0 && (
                  <>
                    <span>·</span>
                    <span>{video.groundTruth.length} issues</span>
                  </>
                )}
              </div>
            </div>
            {onRemove && !disabled && (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 opacity-0 group-hover:opacity-100"
                onClick={(e) => { e.stopPropagation(); onRemove(video.id); }}
              >
                <X className="h-3 w-3" />
              </Button>
            )}
          </div>
        );
      })}
    </div>
  );
}
