// Copyright 2025 Google LLC
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

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";
import StatusBar from "@/components/StatusBar";
import "@/components/login-page.css";
import { Loader2 } from "lucide-react";

export default function LoadingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const notificationText = searchParams.get("notification_text");
    const redirectUrl = notificationText
      ? `/login?notification_text=${encodeURIComponent(notificationText)}`
      : "/login";

    // Simulate loading time
    const timer = setTimeout(() => {
      router.push(redirectUrl);
    }, 2000); // 2 seconds delay

    return () => clearTimeout(timer);
  }, [router, searchParams]);

  return (
    <div className="login-container flex flex-col items-center justify-center bg-zinc-950 text-white">
      <StatusBar />
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="h-12 w-12 animate-spin text-blue-500" />
        <p className="text-sm font-medium text-zinc-400">Loading...</p>
      </div>
    </div>
  );
}