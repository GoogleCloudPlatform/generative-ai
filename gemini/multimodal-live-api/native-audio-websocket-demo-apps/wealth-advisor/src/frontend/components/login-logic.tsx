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

"use client"

import { useRouter, useSearchParams } from "next/navigation"
import { LoginPage } from "@/components/login-page"

export default function LoginLogic() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const handleLogin = () => {
    const notificationText = searchParams.get('notification_text');
    let redirectUrl = "/audio-call";
    if (notificationText) {
      redirectUrl += `?notification_text=${encodeURIComponent(notificationText)}`;
    }
    router.push(redirectUrl);
  };

  return <LoginPage onLogin={handleLogin} />
}