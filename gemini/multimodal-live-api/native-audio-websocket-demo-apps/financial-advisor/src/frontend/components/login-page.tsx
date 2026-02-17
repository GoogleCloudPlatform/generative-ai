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

import StatusBar from './StatusBar';
import "./login-page.css"; // Keeping import to avoid breaking other things if any, but overriding styles

interface LoginPageProps {
  onLogin: () => void;
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const handleLoginClick = () => {
    onLogin();
  };

  return (
    <div className="login-container w-full h-full min-h-screen bg-zinc-900 flex flex-col items-center justify-between py-10 relative overflow-hidden">
      <StatusBar />

      {/* Background decoration */}
      <div className="absolute inset-0 z-0">
        <div className="absolute top-[-20%] right-[-20%] w-[600px] h-[600px] bg-blue-900/20 rounded-full blur-3xl"></div>
        <div className="absolute bottom-[-10%] left-[-10%] w-[500px] h-[500px] bg-purple-900/10 rounded-full blur-3xl"></div>
      </div>

      <div className="z-10 flex-1 flex flex-col items-center justify-center mt-20">
        <div className="w-20 h-20 bg-gradient-to-tr from-blue-500 to-cyan-400 rounded-2xl mb-6 shadow-lg flex items-center justify-center">
          <span className="text-4xl font-bold text-white">W</span>
        </div>
        <h1 className="text-4xl font-bold text-white mb-2">Financial Advisor</h1>
        <p className="text-zinc-400 text-lg">Your financial future, reimagined.</p>
      </div>

      <div className="z-10 w-full max-w-md px-6 flex flex-col items-center gap-4 mb-20">
        <button
          className="w-full bg-white text-black font-bold py-4 rounded-full hover:bg-gray-100 transition shadow-lg active:scale-[0.98]"
          onClick={handleLoginClick}
        >
          Log In
        </button>
        <button
          className="w-full border border-white/20 bg-white/5 backdrop-blur-sm text-white font-bold py-4 rounded-full hover:bg-white/10 transition active:scale-[0.98]"
          onClick={handleLoginClick}
        >
          Don't have an account? Sign Up
        </button>
      </div>
    </div>
  );
}
