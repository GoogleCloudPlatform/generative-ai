// Copyright 2026 Google LLC. This software is provided as-is, without
// warranty or representation for any use or purpose. Your use of it is
// subject to your agreement with Google.
// 
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
// 
//    http://www.apache.org/licenses/LICENSE-2.0
// 
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

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