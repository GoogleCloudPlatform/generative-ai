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