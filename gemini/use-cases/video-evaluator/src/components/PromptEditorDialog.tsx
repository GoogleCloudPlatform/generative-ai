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

import { useState, useEffect, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { VeoModelKey, VEO_MODELS } from '@/lib/veo';
import { Sparkles, Loader2, Music, Clock, Maximize, Image as ImageIcon, X } from 'lucide-react';

interface PromptEditorDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialPrompt: string;
  initialDuration: number;
  initialModel?: VeoModelKey;
  onRegenerate: (options: {
    prompt: string;
    model: VeoModelKey;
    durationSeconds: number;
    aspectRatio: '16:9' | '9:16' | '1:1';
    includeAudio: boolean;
    inputImageBase64?: string;
    strategy: 'creative' | 'similarity';
  }) => void;
  isGenerating: boolean;
}

export function PromptEditorDialog({
  open,
  onOpenChange,
  initialPrompt,
  initialDuration,
  initialModel = 'veo-2.0',
  onRegenerate,
  isGenerating
}: PromptEditorDialogProps) {
  const [prompt, setPrompt] = useState(initialPrompt);
  const [model, setModel] = useState<VeoModelKey>(initialModel);
  const [duration, setDuration] = useState(initialDuration);
  const [aspectRatio, setAspectRatio] = useState<'16:9' | '9:16' | '1:1'>('16:9');
  const [includeAudio, setIncludeAudio] = useState(false);
  const [strategy, setStrategy] = useState<'creative' | 'similarity'>('similarity');
  const [inputImageBase64, setInputImageBase64] = useState<string | undefined>();
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setPrompt(initialPrompt);
      setDuration(Math.min(initialDuration, 8));
    }
  }, [open, initialPrompt, initialDuration]);

  const handleRegenerate = () => {
    onRegenerate({
      prompt,
      model,
      durationSeconds: duration,
      aspectRatio,
      includeAudio,
      inputImageBase64,
      strategy,
    });
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const base64 = event.target?.result as string;
      setInputImageBase64(base64);
    };
    reader.readAsDataURL(file);
  };

  const clearImage = () => {
    setInputImageBase64(undefined);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            Customize Regeneration
          </DialogTitle>
          <DialogDescription>
            Review and edit the prompt and parameters before generating the new video.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 py-4">
          <div className="space-y-2">
            <Label htmlFor="prompt">Regeneration Prompt</Label>
            {!initialPrompt && open ? (
              <div className="flex flex-col items-center justify-center py-10 border rounded-md bg-muted/10 space-y-3">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
                <p className="text-xs text-muted-foreground animate-pulse">Drafting improved prompt with AI...</p>
              </div>
            ) : (
              <>
                <Textarea
                  id="prompt"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Enter instructions for video regeneration..."
                  className="min-h-[120px] text-sm resize-none font-sans"
                />

                {/* Image Upload for Image-to-Video */}
                <div className="flex items-center gap-4 mt-2">
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    ref={fileInputRef}
                    onChange={handleImageUpload}
                  />
                  {!inputImageBase64 ? (
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => fileInputRef.current?.click()}
                      className="text-xs flex items-center gap-2"
                    >
                      <ImageIcon className="h-4 w-4" />
                      Add Starting Image
                    </Button>
                  ) : (
                    <div className="relative group">
                      <div className="h-20 w-32 rounded-md border flex items-center justify-center overflow-hidden bg-black object-cover relative">
                        <img 
                          src={inputImageBase64} 
                          alt="Starting reference" 
                          className="h-full w-full object-cover opacity-80" 
                        />
                        <Button 
                          variant="destructive" 
                          size="icon" 
                          className="absolute h-6 w-6 top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity"
                          onClick={clearImage}
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                      <span className="text-[10px] text-muted-foreground mt-1 absolute -bottom-4 truncate w-full flex justify-center">Image Attached</span>
                    </div>
                  )}
                </div>

                <p className="text-[10px] text-muted-foreground mt-4">
                  Pro-tip: Describe the scene clearly and specify what to avoid. If an image is added, Veo 3 will use it as the first frame.
                </p>
              </>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="flex items-center gap-1.5">
                <Maximize className="h-3.5 w-3.5" /> Model
              </Label>
              <Select value={model} onValueChange={(v) => setModel(v as VeoModelKey)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="veo-2.0">Veo 2.0 (Preview)</SelectItem>
                  <SelectItem value="veo-1.0">Veo 1.0 (Stable)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5" /> Duration
              </Label>
              <Select value={duration.toString()} onValueChange={(v) => setDuration(parseInt(v))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="3">3 Seconds</SelectItem>
                  <SelectItem value="5">5 Seconds</SelectItem>
                  <SelectItem value="8">8 Seconds</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="flex items-center gap-1.5">
                <Maximize className="h-3.5 w-3.5" /> Aspect Ratio
              </Label>
              <Select value={aspectRatio} onValueChange={(v) => setAspectRatio(v as any)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="16:9">Widescreen (16:9)</SelectItem>
                  <SelectItem value="1:1">Square (1:1)</SelectItem>
                  <SelectItem value="9:16">Vertical (9:16)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg border bg-muted/30">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                <div className="space-y-0.5">
                  <Label className="text-sm">Strategy</Label>
                  <p className="text-[10px] text-muted-foreground">Continuity vs Creative</p>
                </div>
              </div>
              <Select value={strategy} onValueChange={(v) => setStrategy(v as any)}>
                <SelectTrigger className="w-[120px] h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="similarity">Continuity</SelectItem>
                  <SelectItem value="creative">Creative</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {strategy === 'similarity' && (
              <div className="col-span-2 flex items-center gap-2 p-2 rounded border border-primary/20 bg-primary/5 text-[10px] text-primary">
                <Clock className="h-3 w-3" />
                <span>
                  <b>Continuity Mode Active:</b> Auto-extracting frames from 0.0s, middle, and end to anchor the generation.
                </span>
              </div>
            )}

            <div className="flex items-center justify-between p-3 rounded-lg border bg-muted/30">
              <div className="flex items-center gap-2">
                <Music className="h-4 w-4 text-primary" />
                <div className="space-y-0.5">
                  <Label htmlFor="audio" className="text-sm">Include Audio</Label>
                  <p className="text-[10px] text-muted-foreground">Add AI soundtrack</p>
                </div>
              </div>
              <Switch
                id="audio"
                checked={includeAudio}
                onCheckedChange={setIncludeAudio}
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={isGenerating}>
            Cancel
          </Button>
          <Button onClick={handleRegenerate} disabled={isGenerating || !prompt.trim()}>
            {isGenerating ? (
              <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Generating...</>
            ) : (
              <><Sparkles className="h-4 w-4 mr-2" /> Start Regeneration</>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
