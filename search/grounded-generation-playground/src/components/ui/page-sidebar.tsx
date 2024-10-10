/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import React from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import ModelSelector from '@/components/ModelSelector';
import { Slider } from '@/components/ui/slider';
import { X } from 'lucide-react';
import Icon from '@/components/ui/icons';

interface PageSidebarProps {
  toggleSidebar: () => void;
  sidebarOpen: boolean;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  googleGrounding: boolean;
  setGoogleGrounding: (enabled: boolean) => void;
  retrievalThreshold: number;
  setRetrievalThreshold: (threshold: number) => void;
  vertexGrounding: boolean;
  setVertexGrounding: (enabled: boolean) => void;
  vertexConfigId: string;
  setVertexConfigId: (configId: string) => void;
}

const PageSidebar: React.FC<PageSidebarProps> = ({
  toggleSidebar,
  sidebarOpen,
  selectedModel,
  setSelectedModel,
  googleGrounding,
  setGoogleGrounding,
  retrievalThreshold,
  setRetrievalThreshold,
  vertexGrounding,
  setVertexGrounding,
  vertexConfigId,
  setVertexConfigId,
}) => {
  return (
    <div
      className={`fixed inset-y-0 left-0 transform ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      } lg:relative lg:translate-x-0 transition duration-200 ease-in-out z-30 w-64 bg-zinc-900 overflow-y-auto border-r border-zinc-700`}
    >
      <div className="flex items-center justify-between p-4">
        <h2 className="text-xl font-semibold text-white">Configure Grounding</h2>
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className="lg:hidden text-white"
        >
          <X className="h-6 w-6" />
        </Button>
      </div>
      <div className="p-4 space-y-6">
        <div className="space-y-4">
          <Label htmlFor="model-selector" className="text-white">
            Model
          </Label>
          <ModelSelector
            selectedModel={selectedModel}
            setSelectedModel={setSelectedModel}
          />
        </div>
        <div className="space-y-2">
          <div className="flex items-center space-x-2">
            <Switch
              id="google-search"
              checked={googleGrounding}
              onCheckedChange={setGoogleGrounding}
            />
            <Label htmlFor="google-search" className="text-white">
              <Icon type="google" className="h-6 w-6 mr-2 text-gray-400" />
              Google Search
            </Label>
          </div>
          {googleGrounding && (
            <div className="space-y-2">
              <Label htmlFor="retrieval-threshold" className="text-white">
                Retrieval Threshold
              </Label>
              <Slider
                id="retrieval-threshold"
                min={0}
                max={1}
                step={0.01}
                value={[retrievalThreshold]}
                onValueChange={(value: number[]) => setRetrievalThreshold(value[0])}
                className="w-full"
              />
              <div className="text-sm text-gray-400">{retrievalThreshold.toFixed(2)}</div>
            </div>
          )}
        </div>
        <div className="space-y-2">
          <div className="flex items-center space-x-2">
            <Switch
              id="vertex-search"
              checked={vertexGrounding}
              onCheckedChange={setVertexGrounding}
            />
            <Label htmlFor="vertex-search" className="text-white truncate">
              <Icon type="vertex" className="h-6 w-6 mr-2" />
              Vertex AI Search
            </Label>
          </div>
          {vertexGrounding && (
            <div className="space-y-2">
              <Label htmlFor="vertex-serving-config" className="text-white">
                Vertex AI Search Serving Config
              </Label>
              <Input
                id="vertex-serving-config"
                value={vertexConfigId}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setVertexConfigId(e.target.value)
                }
                className="bg-zinc-800 text-white border-zinc-700"
                placeholder="Enter your Vertex AI Search Serving Config"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PageSidebar;
