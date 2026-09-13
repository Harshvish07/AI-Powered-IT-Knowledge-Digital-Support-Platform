"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/features/auth/AuthContext";
import { RegisterForm } from "@/features/auth/RegisterForm";

export default function RegisterPage() {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/dashboard");
    }
  }, [status, router]);

  if (status === "authenticated") {
    return null;
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center bg-zinc-50 px-6 py-16 dark:bg-black">
      <h1 className="mb-8 text-xl font-semibold text-zinc-900 dark:text-zinc-50">
        Create an account
      </h1>
      <RegisterForm />
    </div>
  );
}
