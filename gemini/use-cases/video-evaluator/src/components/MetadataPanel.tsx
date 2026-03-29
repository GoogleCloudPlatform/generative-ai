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

import { AnalysisResult } from '@/lib/types';
import { formatTimestamp } from '@/lib/video-utils';
import { FileVideo, Clock, AlertCircle, AlertTriangle, Info, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface MetadataPanelProps {
  result: AnalysisResult;
}

export function MetadataPanel({ result }: MetadataPanelProps) {
  const criticalCount = result.flags.filter(f => f.severity === 'critical').length;
  const warningCount = result.flags.filter(f => f.severity === 'warning').length;
  const infoCount = result.flags.filter(f => f.severity === 'info').length;

  const handleExport = () => {
    const report = {
      videoName: result.videoName,
      analyzedAt: result.createdAt.toISOString(),
      coherenceScore: result.coherenceScore,
      totalFlags: result.flags.length,
      flags: result.flags.map(f => ({
        timestamp: f.timestamp,
        timestampSeconds: f.timestampSeconds,
        startTime: f.timestampSeconds > 0.5 ? f.timestampSeconds - 0.5 : 0,
        endTime: f.timestampSeconds + 1.0,
        severity: f.severity,
        category: f.category,
        description: f.description,
        confidence: f.confidence,
        confirmed: f.confirmed,
        dismissed: f.dismissed,
      })),
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `aegis-report-${result.videoName}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-4">
      <h3 className="text-sm font-semibold text-foreground">Video Info</h3>
      
      <div className="space-y-2 text-sm">
        <div className="flex items-center gap-2 text-muted-foreground">
          <FileVideo className="h-3.5 w-3.5" />
          <span className="truncate">{result.videoName}</span>
        </div>
        <div className="flex items-center gap-2 text-muted-foreground">
          <Clock className="h-3.5 w-3.5" />
          <span className="font-mono">{formatTimestamp(result.videoDuration)}</span>
        </div>
      </div>

      <div className="border-t border-border pt-3 space-y-1.5">
        <div className="flex items-center justify-between text-sm">
          <span className="flex items-center gap-1.5 text-destructive">
            <AlertCircle className="h-3.5 w-3.5" /> Critical
          </span>
          <span className="font-mono text-foreground">{criticalCount}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="flex items-center gap-1.5 text-warning">
            <AlertTriangle className="h-3.5 w-3.5" /> Warning
          </span>
          <span className="font-mono text-foreground">{warningCount}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="flex items-center gap-1.5 text-info">
            <Info className="h-3.5 w-3.5" /> Info
          </span>
          <span className="font-mono text-foreground">{infoCount}</span>
        </div>
      </div>

      <Button variant="outline" size="sm" className="w-full" onClick={handleExport}>
        <Download className="mr-2 h-3.5 w-3.5" /> Export Report
      </Button>
    </div>
  );
}
