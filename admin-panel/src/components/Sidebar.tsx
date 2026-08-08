"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Database, Users } from "lucide-react";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/errors",    label: "Xatolar",   icon: Database },
  { href: "/groups",    label: "Guruhlar",  icon: Users },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 min-h-screen bg-card border-r border-rim flex flex-col py-6 px-3 shrink-0">
      <div className="px-3 mb-8">
        <p className="text-base font-bold text-ink">POS Admin</p>
        <p className="text-xs text-dim mt-0.5">Support Panel</p>
      </div>

      <nav className="flex-1 space-y-0.5">
        {links.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? "bg-ac/10 text-ac"
                  : "text-dim hover:bg-card2 hover:text-ink"
              }`}
            >
              <Icon size={17} />
              {label}
            </Link>
          );
        })}
      </nav>

    </aside>
  );
}
