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

import React from 'react';


interface NotificationBannerProps {
  onClick: () => void;
}

export const NotificationBanner: React.FC<NotificationBannerProps> = ({ onClick }) => {
  return (
    <div 
      className="w-[90%] bg-zinc-800/80 backdrop-blur-md border border-white/10 rounded-2xl p-4 flex items-start gap-4 shadow-lg cursor-pointer transition-transform active:scale-95"
      onClick={onClick}
    >
      <div className="bg-white rounded-xl p-2 flex items-center justify-center shrink-0">
         <div className="text-black font-bold text-xl">W</div> {/* W for Wealth or generic */}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex justify-between items-baseline mb-1">
          <h3 className="text-white font-semibold text-base truncate">Financial Advisor</h3>
          <span className="text-zinc-400 text-xs">now</span>
        </div>
        <p className="text-zinc-200 text-sm leading-tight">
          You have a CD maturing, log in for more information.
        </p>
      </div>
    </div>
  );
};