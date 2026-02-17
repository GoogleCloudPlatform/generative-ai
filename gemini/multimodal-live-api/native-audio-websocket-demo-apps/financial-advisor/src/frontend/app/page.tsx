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

"use client"

import { useRouter } from "next/navigation";
import StatusBar from "@/components/StatusBar";
import { NotificationBanner } from "@/components/notification-banner";

export default function HomePage() {
  const router = useRouter();

  const handleLoginRedirect = () => {
    const notificationText = "You have a CD maturing, log in for more information.";
    router.push(`/loading?notification_text=${encodeURIComponent(notificationText)}`);
  };

  return (
    <div className="home-page-container bg-gradient-to-br from-zinc-900 to-black">
      <StatusBar />
      
      {/* Abstract background pattern */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] rounded-full bg-blue-900/20 blur-3xl"></div>
        <div className="absolute bottom-[-10%] left-[-10%] w-[500px] h-[500px] rounded-full bg-purple-900/10 blur-3xl"></div>
      </div>

      <div
        className="absolute bottom-[300px] w-full flex justify-center z-10"
      >
        <NotificationBanner onClick={handleLoginRedirect} />
      </div>
    </div>
  );
}
