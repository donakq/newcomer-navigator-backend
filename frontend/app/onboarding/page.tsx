"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

/** Onboarding now lives in the six-step /setup wizard. */
export default function Onboarding() {
  const router = useRouter();
  useEffect(() => { router.replace("/setup"); }, [router]);
  return null;
}
