"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    if (Cookies.get("admin_token")) {
      router.replace("/dashboard");
    } else {
      router.replace("/login");
    }
  }, [router]);
  return null;
}
