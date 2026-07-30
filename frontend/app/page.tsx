"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { lerToken } from "@/lib/api";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    router.replace(lerToken() ? "/solicitacoes" : "/login");
  }, [router]);

  return null;
}
