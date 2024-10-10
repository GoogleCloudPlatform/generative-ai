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
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import Icon from '@/components/ui/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { grounding_options } from '@/lib/grounding_options';

interface GroundingOptionProps {
  // this option our of all of them.
  groundingKey: string;
  groundingOptions: string[];
  setGroundingOptions: (model: string[]) => void;
}

const GroundingOption: React.FC<GroundingOptionProps> = ({
  groundingKey,
  groundingOptions,
  setGroundingOptions,
}) => {
  if (!groundingOptions) return null;
  const checked = groundingOptions.includes(groundingKey);
  const setThisGroundingOption = () => {
    if (checked) {
      setGroundingOptions(
        groundingOptions.filter((option: string) => option !== groundingKey),
      );
    } else {
      setGroundingOptions([...groundingOptions, groundingKey]);
    }
  };
  const config = grounding_options[groundingKey];
  const vertexConfigId = '';
  return (
    <div className="space-y-2 select-grounding-option">
      <div className="flex items-center space-x-2">
        <Switch
          id={groundingKey}
          checked={checked}
          onCheckedChange={setThisGroundingOption}
        />
        <Label htmlFor={groundingKey} className="text-white truncate">
          <Icon type={config.icon} className="h-6 w-6 mr-2" />
          {config.data}
        </Label>
      </div>
      {checked && (
        <div className="space-y-2">
          <div className="text-zinc-400">{config.retriever}</div>
          <div className="text-zinc-500 text-sm">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{config.subtext}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
};

export default GroundingOption;
