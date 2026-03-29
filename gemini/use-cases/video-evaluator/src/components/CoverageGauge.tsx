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

import { cn } from '@/lib/utils';

interface CoverageGaugeProps {
  coverage: number; // 0-1
  threshold: number; // 0-1
  size?: 'sm' | 'lg';
}

export function CoverageGauge({ coverage, threshold, size = 'lg' }: CoverageGaugeProps) {
  const percent = Math.round(coverage * 100);
  const meetsThreshold = coverage >= threshold;
  const radius = size === 'lg' ? 54 : 32;
  const stroke = size === 'lg' ? 8 : 5;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (coverage * circumference);
  const svgSize = (radius + stroke) * 2;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: svgSize, height: svgSize }}>
        <svg width={svgSize} height={svgSize} className="-rotate-90">
          {/* Background circle */}
          <circle
            cx={radius + stroke}
            cy={radius + stroke}
            r={radius}
            fill="none"
            strokeWidth={stroke}
            className="stroke-muted"
          />
          {/* Threshold marker */}
          <circle
            cx={radius + stroke}
            cy={radius + stroke}
            r={radius}
            fill="none"
            strokeWidth={stroke}
            strokeDasharray={circumference}
            strokeDashoffset={circumference - (threshold * circumference)}
            className="stroke-muted-foreground/20"
            strokeLinecap="round"
          />
          {/* Coverage arc */}
          <circle
            cx={radius + stroke}
            cy={radius + stroke}
            r={radius}
            fill="none"
            strokeWidth={stroke}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className={cn(
              'transition-all duration-1000 ease-out',
              meetsThreshold ? 'stroke-success' : 'stroke-warning'
            )}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={cn(
            'font-bold font-mono',
            size === 'lg' ? 'text-2xl' : 'text-sm'
          )}>
            {percent}%
          </span>
          {size === 'lg' && (
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
              coverage
            </span>
          )}
        </div>
      </div>
      {size === 'lg' && (
        <p className={cn(
          'text-xs font-medium',
          meetsThreshold ? 'text-success' : 'text-warning'
        )}>
          {meetsThreshold ? '✓ Meets threshold' : `Below ${Math.round(threshold * 100)}% threshold`}
        </p>
      )}
    </div>
  );
}
