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
import { Menu } from 'lucide-react';

interface PageHeaderProps {
  toggleSidebar: () => void;
}

const PageHeader: React.FC<PageHeaderProps> = ({ toggleSidebar }) => {
  return (
    <header className="bg-zinc-900 shadow-md border-b border-zinc-800">
      <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between">
          <h1
            className="text-2xl font-semibold text-transparent bg-clip-text"
            style={{
              backgroundImage:
                'linear-gradient(72.83deg, #4285F4 11.63%, #9b72cb 40.43%, #d96570 68.07%)',
            }}
          >
            Vertex AI Search Grounded Generation Playground
          </h1>
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className="lg:hidden text-white"
          >
            <Menu className="h-6 w-6" />
          </Button>
        </div>
      </div>
    </header>
  );
};

export default PageHeader;
