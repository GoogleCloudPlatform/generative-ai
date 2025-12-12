"use client"

import { Suspense } from 'react';
import AudioCallPageContent from '@/components/audio-call-page-content';

export default function AudioCallPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <AudioCallPageContent />
    </Suspense>
  );
}
