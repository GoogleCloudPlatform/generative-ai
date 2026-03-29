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

import { Flag } from '@/lib/types';
import { IssueCard } from './IssueCard';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Download } from 'lucide-react';

interface IssueListProps {
  flags: Flag[];
  selectedFlagId?: string;
  onFlagClick: (flag: Flag) => void;
  onConfirm: (flagId: string) => void;
  onDismiss: (flagId: string) => void;
  compact?: boolean;
}

export function IssueList({ flags, selectedFlagId, onFlagClick, onConfirm, onDismiss, compact }: IssueListProps) {
  if (flags.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="text-muted-foreground text-sm">No issues detected</p>
        <p className="text-muted-foreground/60 text-xs mt-1">Video appears coherent</p>
      </div>
    );
  }

  const critical = flags.filter(f => f.severity === 'critical' && !f.dismissed);
  const warnings = flags.filter(f => f.severity === 'warning' && !f.dismissed);
  const info = flags.filter(f => f.severity === 'info' && !f.dismissed);
  const dismissed = flags.filter(f => f.dismissed);

  const exportableFlags = flags.filter(f => f.confirmed);

  const handleExport = () => {
    if (exportableFlags.length === 0) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(exportableFlags, null, 2));
    const downloadNode = document.createElement('a');
    downloadNode.setAttribute("href", dataStr);
    downloadNode.setAttribute("download", `reviewed_flags_export_${Date.now()}.json`);
    document.body.appendChild(downloadNode);
    downloadNode.click();
    downloadNode.remove();
  };

  const content = (
    <div className="space-y-4">
      {exportableFlags.length > 0 && !compact && (
        <div className="flex justify-end pr-3">
          <Button variant="outline" size="sm" onClick={handleExport} className="w-full sm:w-auto">
            <Download className="h-4 w-4 mr-2" />
            Export Reviewed to JSON
          </Button>
        </div>
      )}
      <div className="space-y-2">
      {[...critical, ...warnings, ...info, ...dismissed].map(flag => (
        <IssueCard
          key={flag.id}
          flag={flag}
          isSelected={flag.id === selectedFlagId}
          onClick={() => onFlagClick(flag)}
          onConfirm={() => onConfirm(flag.id)}
          onDismiss={() => onDismiss(flag.id)}
          compact={compact}
        />
      ))}
    </div>
    </div>
  );

  if (compact) return content;

  return (
    <ScrollArea className="h-[500px]">
      <div className="pr-3">
        {content}
      </div>
    </ScrollArea>
  );
}
