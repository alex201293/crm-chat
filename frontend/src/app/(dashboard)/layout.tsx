"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

const navigation = [
  { name: "Chat", href: "/chat" },
  { name: "CRM", href: "/crm" },
  { name: "Campañas", href: "/campaigns" },
  { name: "Conocimiento", href: "/knowledge" },
  { name: "Panel", href: "/dashboard" },
  { name: "Configuración", href: "/settings" },
];

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [user, setUser] = useState<{ full_name?: string; tenant_name?: string } | null>(null);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("user");
      if (stored) setUser(JSON.parse(stored));
    } catch {
      // ignore
    }
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Sidebar */}
      <aside className="hidden w-64 flex-shrink-0 border-r border-gray-200 bg-white lg:flex lg:flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center gap-3 px-6 border-b border-gray-200">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
            <span className="text-sm font-bold text-white">C</span>
          </div>
          <span className="text-lg font-bold text-gray-900">CRM Chat</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-3 py-4">
          {navigation.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-blue-50 text-blue-700"
                    : "text-gray-700 hover:bg-gray-100"
                )}
              >
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* User info */}
        <div className="border-t border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-100">
              <span className="text-sm font-semibold text-blue-700">
                {user?.full_name?.[0] ?? "A"}
              </span>
            </div>
            <div className="flex-1 truncate">
              <p className="truncate text-sm font-medium text-gray-900">
                {user?.full_name ?? "Usuario"}
              </p>
              <p className="truncate text-xs text-gray-500">
                {user?.tenant_name ?? "Mi Empresa"}
              </p>
            </div>
            <button
              onClick={() => {
                localStorage.clear();
                window.location.href = "/login";
              }}
              className="text-xs text-gray-400 hover:text-red-500"
              title="Cerrar sesión"
            >
              ✕
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6">
          <h1 className="text-lg font-semibold text-gray-900">
            {navigation.find((n) => pathname.startsWith(n.href))?.name ?? "Panel"}
          </h1>
        </header>
        <div className="flex-1 overflow-auto">{children}</div>
      </main>
    </div>
  );
}
