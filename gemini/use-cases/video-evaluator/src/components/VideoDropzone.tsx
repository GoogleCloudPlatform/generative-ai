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

import { useCallback, useState } from 'react';
import { Upload, Link, Film } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

interface VideoDropzoneProps {
  onFileSelected: (file: File) => void;
  isAnalyzing: boolean;
}

export function VideoDropzone({ onFileSelected, isAnalyzing }: VideoDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [showUrlInput, setShowUrlInput] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file && (file.type.startsWith('video/') || file.type.startsWith('image/'))) {
        onFileSelected(file);
      }
    },
    [onFileSelected]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onFileSelected(file);
    },
    [onFileSelected]
  );

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      className={cn(
        'relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 transition-all duration-300',
        isDragging
          ? 'border-primary bg-primary/5 scale-[1.01]'
          : 'border-border hover:border-primary/50 hover:bg-card/50',
        isAnalyzing && 'pointer-events-none opacity-50'
      )}
    >
      <div className="flex flex-col items-center gap-4">
        <div className="rounded-full bg-primary/10 p-4">
          <Film className="h-8 w-8 text-primary" />
        </div>
        <div className="text-center">
          <p className="text-lg font-medium text-foreground">
            Drop your media here
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            MP4, WebM, MOV, JPG, PNG — up to 100MB
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label>
            <input
              type="file"
              accept="video/*, image/*"
              onChange={handleFileInput}
              className="hidden"
              disabled={isAnalyzing}
            />
            <Button variant="default" size="sm" asChild disabled={isAnalyzing}>
              <span className="cursor-pointer">
                <Upload className="mr-2 h-4 w-4" />
                Browse Files
              </span>
            </Button>
          </label>
        </div>
      </div>
    </div>
  );
}
