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

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import BatchResultsPage from './BatchResults';
import { useBatchEvaluation } from '@/hooks/useBatchEvaluation';

/**
 * Wrapper page that manages batch state between upload and results views.
 * This is needed because BatchUpload navigates to results after evaluation.
 */
const BatchWrapper = () => {
  // This page is accessed after evaluation completes.
  // For now, redirect back to batch upload since state is in-memory.
  const navigate = useNavigate();
  
  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="text-center space-y-4">
        <p className="text-muted-foreground">Batch results are shown after evaluation completes.</p>
        <button
          className="text-primary underline text-sm"
          onClick={() => navigate('/batch')}
        >
          Go to Batch Upload
        </button>
      </div>
    </div>
  );
};

export default BatchWrapper;
