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
import { useNavigate } from 'react-router-dom';
import { Shield, ArrowLeft, Upload, Play, Film, Settings, AlertTriangle, CheckCircle, Wand2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ApiKeyDialog } from '@/components/ApiKeyDialog';
import { AgentSettings } from '@/components/AgentSettings';
import { useBatchEvaluation } from '@/hooks/useBatchEvaluation';
import { hasApiKey } from '@/lib/gemini-config';
import { cn } from '@/lib/utils';
import { AgentConfig } from '@/lib/types';
import { getStoredAgentConfigs, saveAgentConfigs } from '@/lib/agent-storage';

const BatchUpload = () => {
  const navigate = useNavigate();
  const {
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
  } = useBatchEvaluation();

  const [isDragging, setIsDragging] = useState(false);
  const [showApiDialog, setShowApiDialog] = useState(!hasApiKey());
  const [agentConfigs, setAgentConfigs] = useState<AgentConfig[]>(getStoredAgentConfigs());

  const handleConfigsChange = (configs: AgentConfig[]) => {
    setAgentConfigs(configs);
    saveAgentConfigs(configs);
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('video/') || f.type.startsWith('image/'));
    if (files.length > 0) addFiles(files);
  }, [addFiles]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []).filter(f => f.type.startsWith('video/') || f.type.startsWith('image/'));
    if (files.length > 0) addFiles(files);
  }, [addFiles]);

  const allPending = items.every(i => i.status === 'pending');
  const allAnalyzed = items.length > 0 && items.every(i => i.status === 'done' && !i.regeneratedResult);
  const allRegenerated = items.length > 0 && items.every(i => i.regeneratedResult);

  return (
    <div className="min-h-screen bg-background">
      <ApiKeyDialog open={showApiDialog} onOpenChange={setShowApiDialog} onSave={() => {}} />

      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container flex items-center justify-between h-14 px-4">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => navigate('/')}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <Shield className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-bold tracking-tight text-foreground">Batch Remediation Lab</h1>
          </div>
          <Button variant="ghost" size="icon" onClick={() => setShowApiDialog(true)}>
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </header>

      <main className="container px-4 py-8">
        
        {/* Controls Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <div className="lg:col-span-1 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Batch Controls</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                
                <div
                  onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleDrop}
                  className={cn(
                    'flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-all',
                    isDragging ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50',
                    isProcessing && 'pointer-events-none opacity-50'
                  )}
                >
                  <Upload className="h-6 w-6 text-muted-foreground mb-2" />
                  <p className="text-xs text-muted-foreground mb-2 text-center">Drop sample media (Images/Videos) here</p>
                  <label>
                    <input
                      type="file"
                      accept="video/*, image/*"
                      multiple
                      onChange={handleFileInput}
                      className="hidden"
                      disabled={isProcessing}
                    />
                    <Button variant="secondary" size="sm" asChild>
                      <span className="cursor-pointer">Browse Files</span>
                    </Button>
                  </label>
                </div>

                <AgentSettings
                  configs={agentConfigs}
                  onChange={handleConfigsChange}
                  disabled={isProcessing}
                />

                <div className="pt-4 border-t border-border flex flex-col gap-2">
                  <Button 
                    className="w-full" 
                    onClick={() => startBatchAnalysis(agentConfigs)}
                    disabled={isProcessing || items.length === 0 || !allPending}
                  >
                    <Play className="h-4 w-4 mr-2" />
                    1. Analyze Batch
                  </Button>
                  
                  <Button 
                    variant="outline"
                    className="w-full" 
                    onClick={generateSweepingFix}
                    disabled={isProcessing || items.length === 0 || !allAnalyzed}
                  >
                    <Shield className="h-4 w-4 mr-2" />
                    2. Generate Sweeping Fix
                  </Button>

                  <Button 
                    variant="outline"
                    className="w-full text-indigo-400 border-indigo-500/30 hover:bg-indigo-500/10" 
                    onClick={generateBatchInsights}
                    disabled={isProcessing || items.length === 0 || !allAnalyzed}
                  >
                    <CheckCircle className="h-4 w-4 mr-2" />
                    3. Summarize Batch Insights
                  </Button>

                  <Button 
                    variant="secondary"
                    className="w-full border-blue-500/30 text-blue-400 hover:bg-blue-500/10" 
                    onClick={() => startBatchRegeneration(globalFixPrompt!)}
                    disabled={isProcessing || !globalFixPrompt}
                  >
                    <Wand2 className="h-4 w-4 mr-2" />
                    4. Regenerate with Fix
                  </Button>

                  <Button variant="ghost" size="sm" onClick={clearBatch} disabled={isProcessing}>Clear Batch</Button>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="lg:col-span-2 space-y-6">
            
            {globalFixPrompt && (
               <Card className="border-blue-500/30 bg-blue-500/5">
                 <CardHeader className="pb-2">
                   <CardTitle className="text-sm flex items-center gap-2 text-blue-400">
                     <Wand2 className="h-4 w-4" />
                     Gemini Sweeping Fix Recommendation
                   </CardTitle>
                 </CardHeader>
                 <CardContent>
                    <p className="text-sm opacity-90 leading-relaxed font-mono bg-background/50 p-4 rounded text-blue-200">
                      {globalFixPrompt}
                    </p>
                 </CardContent>
               </Card>
            )}

            {batchInsights && (
               <Card className="border-indigo-500/30 bg-indigo-500/5 mt-4 mb-6">
                 <CardHeader className="pb-2">
                   <CardTitle className="text-sm flex items-center gap-2 text-indigo-400">
                     <CheckCircle className="h-4 w-4" />
                     Prompt Engineering Insights (Batch Summary)
                   </CardTitle>
                 </CardHeader>
                 <CardContent>
                    <p className="text-sm opacity-90 leading-relaxed font-sans bg-background/60 p-5 rounded text-indigo-100 whitespace-pre-wrap">
                      {batchInsights}
                    </p>
                 </CardContent>
               </Card>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {items.map(item => (
                <Card key={item.id} className={cn("overflow-hidden border-2", 
                  item.status === 'error' ? "border-red-500/50" : 
                  item.status === 'analyzing' || item.status === 'regenerating' ? "border-primary/50 animate-pulse" : "border-border"
                )}>
                  <div className="p-4 flex gap-4">
                    <div className="w-1/3 aspect-video bg-muted rounded overflow-hidden flex items-center justify-center">
                      <Film className="h-6 w-6 text-muted-foreground/30" />
                    </div>
                    <div className="w-2/3 flex flex-col">
                      <h3 className="font-medium text-sm truncate">{item.file.name}</h3>
                      <div className="text-xs text-muted-foreground mb-auto">{item.status}</div>
                      
                      {item.originalResult && (
                        <div className="mt-2 text-xs flex justify-between border-t border-border/50 pt-2">
                          <span className="text-muted-foreground">Original Score:</span>
                          <span className={cn("font-bold", 
                            item.originalResult.coherenceScore > 80 ? "text-green-500" : 
                            item.originalResult.coherenceScore > 50 ? "text-yellow-500" : "text-red-500"
                          )}>{item.originalResult.coherenceScore}</span>
                        </div>
                      )}

                      {item.regeneratedResult && (
                        <div className="mt-1 text-xs flex justify-between">
                          <span className="text-muted-foreground flex items-center gap-1">
                            <Wand2 className="h-3 w-3" /> New Score:
                          </span>
                          <span className={cn("font-bold", 
                            item.regeneratedResult.coherenceScore > 80 ? "text-green-500" : 
                            item.regeneratedResult.coherenceScore > 50 ? "text-yellow-500" : "text-red-500"
                          )}>{item.regeneratedResult.coherenceScore}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </Card>
              ))}
              
              {items.length === 0 && (
                <div className="col-span-full h-64 border border-dashed rounded-lg flex flex-col items-center justify-center text-muted-foreground">
                  No items in batch.
                </div>
              )}
            </div>
          </div>
        </div>

      </main>
    </div>
  );
};

export default BatchUpload;
