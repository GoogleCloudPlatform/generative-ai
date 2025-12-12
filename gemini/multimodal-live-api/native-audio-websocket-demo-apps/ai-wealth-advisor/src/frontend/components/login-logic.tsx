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
