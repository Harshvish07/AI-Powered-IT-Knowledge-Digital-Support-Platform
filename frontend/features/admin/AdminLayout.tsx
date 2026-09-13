"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/features/auth/AuthContext";

const NAV_ITEMS = [
  { href: "/admin", label: "Dashboard" },
  { href: "/admin/tickets", label: "Tickets" },
  { href: "/knowledge", label: "Knowledge Base" },
  { href: "/admin/users", label: "Users" },
  { href: "/admin/conversations", label: "AI Conversations" },
];

function isActive(pathname: string | null, href: string): boolean {
  if (href === "/admin") return pathname === "/admin";
  return pathname === href || (pathname?.startsWith(`${href}/`) ?? false);
}

interface AdminLayoutProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}

export function AdminLayout({ title, description, actions, children }: AdminLayoutProps) {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  return (
    <div className="flex min-h-screen flex-1 flex-col bg-zinc-50 dark:bg-black">
      <header className="flex items-center justify-between border-b border-zinc-200 bg-white px-4 py-3 sm:px-8 dark:border-zinc-800 dark:bg-zinc-950">
        <div className="flex items-center gap-4">
          <Link href="/dashboard" className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
            &larr; Main site
          </Link>
          <span className="hidden text-sm text-zinc-300 sm:inline dark:text-zinc-700">|</span>
          <span className="hidden text-sm font-medium text-zinc-500 sm:inline dark:text-zinc-400">
            Admin
          </span>
        </div>
        <div className="flex items-center gap-4">
          {user ? (
            <span className="hidden text-sm text-zinc-500 sm:inline dark:text-zinc-400">
              {user.full_name}
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
      </header>

      {/* Small screens: horizontal scrollable nav instead of a sidebar. */}
      <nav className="flex gap-1 overflow-x-auto border-b border-zinc-200 bg-white px-4 py-2 sm:hidden dark:border-zinc-800 dark:bg-zinc-950">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`shrink-0 rounded-md px-3 py-1.5 text-sm font-medium ${
              isActive(pathname, item.href)
                ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                : "text-zinc-600 dark:text-zinc-400"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="flex flex-1">
        <aside className="hidden w-56 shrink-0 border-r border-zinc-200 bg-white sm:block dark:border-zinc-800 dark:bg-zinc-950">
          <nav className="flex flex-col gap-1 p-4">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-md px-3 py-2 text-sm font-medium ${
                  isActive(pathname, item.href)
                    ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                    : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-900"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <div className="border-b border-zinc-200 bg-white px-4 py-6 sm:px-8 dark:border-zinc-800 dark:bg-zinc-950">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">{title}</h1>
                {description ? (
                  <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">{description}</p>
                ) : null}
              </div>
              {actions}
            </div>
          </div>

          <main className="flex-1 px-4 py-8 sm:px-8 sm:py-10">{children}</main>
        </div>
      </div>
    </div>
  );
}
