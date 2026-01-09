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

"use client";

import React from 'react';
import { usePathname } from 'next/navigation';
import { Wifi, Battery, Signal } from 'lucide-react';
import './StatusBar.css';

const StatusBar = () => {
    const pathname = usePathname();

    // Determine if we need a transparent background or black/dark one
    // For home ('/') and login ('/login') we might want transparent if on top of an image/gradient
    const isTransparent = pathname === '/' || pathname === '/login' || pathname === '/loading';

    return (
        <div className={`status-bar ${isTransparent ? 'bg-transparent' : 'bg-black'} text-white w-full flex justify-between items-center px-6 py-2 z-50 fixed top-0 left-0`}>
            <div className="time font-semibold text-sm">
                9:41
            </div>
            <div className="right-side flex items-center gap-2">
                <Signal size={16} strokeWidth={2.5} />
                <Wifi size={16} strokeWidth={2.5} />
                <Battery size={20} strokeWidth={2.5} />
            </div>
        </div>
    );
};

export default StatusBar;