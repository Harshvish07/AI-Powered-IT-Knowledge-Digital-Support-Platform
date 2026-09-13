"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/features/auth/AuthContext";

export function NavBar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  function linkClass(href: string) {
    const active = pathname === href || pathname?.startsWith(`${href}/`);
    return `text-sm font-medium ${
      active
        ? "text-zinc-900 dark:text-zinc-50"
        : "text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-50"
    }`;
  }

  return (
    <nav className="flex items-center justify-between border-b border-zinc-200 bg-white px-8 py-4 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex items-center gap-6">
        <Link href="/dashboard" className={linkClass("/dashboard")}>
          Dashboard
        </Link>
        <Link href="/knowledge" className={linkClass("/knowledge")}>
          Knowledge Base
        </Link>
        <Link href="/assistant" className={linkClass("/assistant")}>
          Assistant
        </Link>
        <Link href="/tickets" className={linkClass("/tickets")}>
          Tickets
        </Link>
        {user?.role === "ADMIN" ? (
          <>
            <Link href="/admin/tickets" className={linkClass("/admin/tickets")}>
              All Tickets
            </Link>
            <Link href="/admin" className={linkClass("/admin")}>
              Admin
            </Link>
          </>
        ) : null}
      </div>
      <div className="flex items-center gap-4">
        {user ? (
          <span className="text-sm text-zinc-500 dark:text-zinc-400">
            {user.full_name} &middot; {user.role}
          </span>
        ) : null}
        <button
          type="button"
          onClick={handleLogout}
          className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium text-zinc-700 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
        >
          Log out
        </button>
      </div>
    </nav>
  );
}
