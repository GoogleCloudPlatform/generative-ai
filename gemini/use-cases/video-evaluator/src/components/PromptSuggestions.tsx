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
import { Lightbulb, Check, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PromptSuggestion, GroundTruthIssue } from '@/lib/batch-types';
import { suggestImprovements } from '@/lib/prompt-optimizer';
import { Badge } from '@/components/ui/badge';

interface PromptSuggestionsProps {
  unmatchedIssues: GroundTruthIssue[];
  onAccept?: (suggestion: PromptSuggestion) => void;
}

export function PromptSuggestionsPanel({ unmatchedIssues, onAccept }: PromptSuggestionsProps) {
  const [suggestions, setSuggestions] = useState<PromptSuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const results = await suggestImprovements(unmatchedIssues);
      setSuggestions(results);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate suggestions');
    } finally {
      setIsLoading(false);
    }
  };

  if (unmatchedIssues.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Lightbulb className="h-4 w-4 text-warning" />
          <CardTitle className="text-sm">Improvement Suggestions</CardTitle>
        </div>
        <p className="text-xs text-muted-foreground">
          {unmatchedIssues.length} issue{unmatchedIssues.length !== 1 ? 's' : ''} not detected by current agents
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {suggestions.length === 0 && !isLoading && (
          <Button size="sm" variant="secondary" onClick={handleGenerate}>
            <Lightbulb className="h-3.5 w-3.5 mr-1.5" />
            Generate Suggestions
          </Button>
        )}

        {isLoading && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-4 justify-center">
            <Loader2 className="h-4 w-4 animate-spin" /> Analyzing unmatched issues...
          </div>
        )}

        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}

        {suggestions.map(suggestion => (
          <div
            key={suggestion.id}
            className="rounded-md border border-border p-3 space-y-2"
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-sm font-medium text-foreground">{suggestion.title}</p>
                <Badge variant="outline" className="text-[10px] mt-1">
                  {suggestion.type === 'modify_existing' ? `Modify: ${suggestion.agentType}` : 'New Agent'}
                </Badge>
              </div>
              {onAccept && (
                <Button
                  size="sm"
                  variant={suggestion.accepted ? 'secondary' : 'default'}
                  className="shrink-0"
                  onClick={() => {
                    setSuggestions(prev =>
                      prev.map(s => s.id === suggestion.id ? { ...s, accepted: true } : s)
                    );
                    onAccept(suggestion);
                  }}
                  disabled={suggestion.accepted}
                >
                  {suggestion.accepted ? (
                    <><Check className="h-3 w-3 mr-1" /> Accepted</>
                  ) : 'Accept'}
                </Button>
              )}
            </div>
            <p className="text-xs text-muted-foreground">{suggestion.description}</p>
            {suggestion.suggestedPrompt && (
              <pre className="text-[10px] bg-muted/50 rounded p-2 whitespace-pre-wrap font-mono text-muted-foreground max-h-32 overflow-auto">
                {suggestion.suggestedPrompt}
              </pre>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
