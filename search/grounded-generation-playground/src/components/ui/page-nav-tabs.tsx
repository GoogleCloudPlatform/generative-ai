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

import Link from 'next/link';

interface PageNavTabsProps {
  pathname: string;
}

const PageNavTabs: React.FC<PageNavTabsProps> = ({ pathname }) => {
  return (
    <div className="bg-zinc-900">
      <div className="max-w-7xl mx-auto">
        <nav className="flex">
          <Link
            href="/comparison"
            className={`flex-1 text-center py-4 text-sm font-medium border-b-2 ${
              pathname === '/comparison'
                ? 'border-blue-500 text-blue-500'
                : 'border-transparent text-gray-600 hover:text-white hover:border-gray-300'
            }`}
          >
            <h2 className="text-4xl font-semibold mb-0">Comparison Mode</h2>
          </Link>
          <Link
            href="/chat"
            className={`flex-1 text-center py-4 text-sm font-medium border-b-2 ${
              pathname === '/chat'
                ? 'border-blue-500 text-blue-500'
                : 'border-transparent text-gray-600 hover:text-white hover:border-gray-300'
            }`}
          >
            <h2 className="text-4xl font-semibold mb-0">Chat interface</h2>
          </Link>
        </nav>
      </div>
    </div>
  );
};

export default PageNavTabs;
