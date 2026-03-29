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

import { CheckCircle2, XCircle } from 'lucide-react';
import { GroundTruthIssue, VideoEntry } from '@/lib/batch-types';

interface CoverageSummaryProps {
  video: VideoEntry;
}

export function CoverageSummary({ video }: CoverageSummaryProps) {
  const matched = video.groundTruth.filter(gt => gt.matched);
  const unmatched = video.unmatchedIssues;

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
        Coverage Breakdown
      </h4>
      {video.groundTruth.length === 0 ? (
        <p className="text-sm text-muted-foreground">No ground truth issues annotated</p>
      ) : (
        <div className="space-y-1.5">
          {matched.map(gt => (
            <IssueRow key={gt.id} issue={gt} matched />
          ))}
          {unmatched.map(gt => (
            <IssueRow key={gt.id} issue={gt} matched={false} />
          ))}
        </div>
      )}
    </div>
  );
}

function IssueRow({ issue, matched }: { issue: GroundTruthIssue; matched: boolean }) {
  return (
    <div className="flex items-start gap-2 rounded-md bg-muted/30 px-2.5 py-2 text-sm">
      {matched ? (
        <CheckCircle2 className="h-4 w-4 text-success shrink-0 mt-0.5" />
      ) : (
        <XCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
      )}
      <div className="min-w-0">
        <p className="text-foreground">{issue.description}</p>
        <p className="text-xs text-muted-foreground">
          {formatSec(issue.startTime)}
          {issue.endTime ? ` – ${formatSec(issue.endTime)}` : ''}
        </p>
      </div>
    </div>
  );
}

function formatSec(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
}
