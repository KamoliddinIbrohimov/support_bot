"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";
import { loginWithTelegram } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (Cookies.get("admin_token")) {
      router.replace("/dashboard");
      return;
    }

    (window as unknown as Record<string, unknown>).onTelegramAuth = async (
      user: Record<string, string | number>
    ) => {
      try {
        const res = await loginWithTelegram(user);
        Cookies.set("admin_token", res.data.access_token, { expires: 1 });
        router.replace("/dashboard");
      } catch (e: unknown) {
        const msg =
          (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          "Kirish amalga oshmadi";
        setError(msg);
      }
    };

    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.async = true;
    script.setAttribute(
      "data-telegram-login",
      process.env.NEXT_PUBLIC_BOT_USERNAME || "POSAssist_bot"
    );
    script.setAttribute("data-size", "large");
    script.setAttribute("data-onauth", "onTelegramAuth(user)");
    script.setAttribute("data-request-access", "write");
    containerRef.current?.appendChild(script);
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200">
      <div className="bg-white p-10 rounded-2xl shadow-lg text-center space-y-6 w-full max-w-sm">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-gray-900">POS Assist</h1>
          <p className="text-sm text-gray-500">Admin Panel</p>
        </div>

        <div className="flex justify-center">
          <div ref={containerRef} />
        </div>

        {error && (
          <p className="text-sm text-red-500 bg-red-50 rounded-lg px-4 py-2">{error}</p>
        )}

        <p className="text-xs text-gray-400">
          Faqat adminlar kirishi mumkin
        </p>
      </div>
    </div>
  );
}
