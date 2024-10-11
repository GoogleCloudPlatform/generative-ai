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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Card, CardContent } from '@/components/ui/card';
import Icon from '@/components/ui/icons';

interface ExampleQuestion {
  text: string;
  icon?: string; // Make icon optional to match the other definition
}

interface ExampleQuestionGreetingProps {
  greeting: string;
  exampleQuestions: ExampleQuestion[];
  onClick: (queryText: string) => void;
}

const ExampleQuestionGreeting: React.FC<ExampleQuestionGreetingProps> = ({
  greeting,
  exampleQuestions,
  onClick,
}) => {
  return (
    <div className="text-left mb-8">
      <p className="text-xl text-gray-300 mb-6">{greeting}</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {exampleQuestions.map((query, index) => (
          <TooltipProvider key={index}>
            <Tooltip>
              <TooltipTrigger asChild>
                <Card className="bg-zinc-800 border-zinc-700 hover:bg-zinc-700 transition-colors duration-200">
                  <CardContent
                    className="flex items-center p-4 cursor-pointer"
                    onClick={() => onClick(query.text)}
                  >
                    {query.icon && (
                      <Icon type={query.icon} className="h-6 w-6 mr-2 text-gray-400" />
                    )}
                    <p className="text-sm text-gray-300 truncate">{query.text}</p>
                  </CardContent>
                </Card>
              </TooltipTrigger>
              <TooltipContent>
                <p>{query.text}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ))}
      </div>
    </div>
  );
};

export default ExampleQuestionGreeting;
