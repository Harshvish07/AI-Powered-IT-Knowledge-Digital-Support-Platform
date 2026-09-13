"use client";

import { useMemo, useState } from "react";

import { AdminLayout } from "@/features/admin/AdminLayout";
import { useAdminUsers } from "@/features/admin/useAdminUsers";
import { UserRow } from "@/features/admin/UserRow";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import type { UserRole } from "@/types/api";

const ROLES: UserRole[] = ["EMPLOYEE", "ADMIN"];

export default function AdminUsersPage() {
  const { status, user } = useRequireAuth({ role: "ADMIN" });
  const { users, loading, error, refresh } = useAdminUsers();
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");

  const filteredUsers = useMemo(() => {
    const query = search.trim().toLowerCase();
    return users.filter((row) => {
      if (roleFilter && row.role !== roleFilter) return false;
      if (!query) return true;
      return row.full_name.toLowerCase().includes(query) || row.email.toLowerCase().includes(query);
    });
  }, [users, search, roleFilter]);

  if (status !== "authenticated" || user?.role !== "ADMIN") {
    return (
      <div className="flex flex-1 items-center justify-center bg-zinc-50 dark:bg-black">
        <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading...</p>
      </div>
    );
  }

  return (
    <AdminLayout title="Users" description="Manage user accounts and access">
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="search"
          placeholder="Search by name or email..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="w-64 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
        />
        <select
          value={roleFilter}
          onChange={(event) => setRoleFilter(event.target.value)}
          className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
        >
          <option value="">All roles</option>
          {ROLES.map((role) => (
            <option key={role} value={role}>
              {role}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-6 overflow-x-auto rounded-lg border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        {loading ? (
          <p className="p-6 text-sm text-zinc-500 dark:text-zinc-400">Loading users...</p>
        ) : error ? (
          <p className="p-6 text-sm text-red-600 dark:text-red-400">{error}</p>
        ) : filteredUsers.length === 0 ? (
          <p className="p-6 text-sm text-zinc-500 dark:text-zinc-400">
            {users.length === 0 ? "No users found." : "No users match the current filters."}
          </p>
        ) : (
          <table className="w-full min-w-140 text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-200 text-xs uppercase tracking-wide text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
                <th className="px-4 py-3 font-medium">User</th>
                <th className="px-4 py-3 font-medium">Role</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Joined</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="[&>tr>td]:px-4">
              {filteredUsers.map((row) => (
                <UserRow key={row.id} targetUser={row} onChanged={refresh} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </AdminLayout>
  );
}
