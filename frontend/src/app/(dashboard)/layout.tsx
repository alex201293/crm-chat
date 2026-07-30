"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth.store";
import { type ReactNode } from "react";

const navigation = [
  { name: "Chat", href: "/chat", icon: "MessageSquare" },
  { name: "CRM", href: "/crm", icon: "Users" },
  { name: "Campañas", href: "/campaigns", icon: "Megaphone" },
  { name: "Conocimiento", href: "/knowledge", icon: "BookOpen" },
  { name: "Panel", href: "/dashboard", icon: "BarChart3" },
  { name: "Configuración", href: "/settings", icon: "Settings" },
];

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user, isAuthenticated } = useAuthStore();

  // In production, redirect to login if not authenticated
  // For now, render the layout

  return (
    <div className="flex h-screen overflow-hidden bg-surface">
      {/* Sidebar */}
      <aside className="hidden w-64 flex-shrink-0 border-r border-gray-200 bg-surface-secondary dark:border-gray-700 lg:flex lg:flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center gap-2 px-6">
          <div className="h-8 w-8 rounded-lg bg-brand-600" />
          <span className="text-lg font-bold text-gray-900 dark:text-gray-100">
            CRM Chat
          </span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-3 py-4" aria-label="Main navigation">
          {navigation.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-brand-50 text-brand-700 dark:bg-brand-900/20 dark:text-brand-400"
                    : "text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                )}
                aria-current={isActive ? "page" : undefined}
              >
                <span className="h-5 w-5" aria-hidden="true" />
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* User info */}
        <div className="border-t border-gray-200 p-4 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-full bg-brand-100 dark:bg-brand-900/30" />
            <div className="flex-1 truncate">
              <p className="truncate text-sm font-medium text-gray-900 dark:text-gray-100">
                {user?.full_name || "Usuario"}
              </p>
              <p className="truncate text-xs text-gray-500 dark:text-gray-400">
                {user?.tenant_name || "Organización"}
              </p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-16 items-center justify-between border-b border-gray-200 px-6 dark:border-gray-700">
          <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {navigation.find((n) => pathname.startsWith(n.href))?.name || "Dashboard"}
          </h1>
          <div className="flex items-center gap-4">
            {/* Notifications, settings, etc. */}
          </div>
        </header>

        {/* Page content */}
        <div className="flex-1 overflow-auto">{children}</div>
      </main>
    </div>
  );
}
