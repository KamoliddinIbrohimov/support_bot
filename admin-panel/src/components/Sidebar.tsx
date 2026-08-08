"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import Cookies from "js-cookie";
import { LayoutDashboard, Database, Users, LogOut } from "lucide-react";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/errors", label: "Xatolar", icon: Database },
  { href: "/groups", label: "Guruhlar", icon: Users },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const logout = () => {
    Cookies.remove("admin_token");
    router.push("/login");
  };

  return (
    <aside className="w-56 min-h-screen bg-gray-900 text-white flex flex-col py-6 px-3 shrink-0">
      <div className="px-3 mb-8">
        <p className="text-lg font-bold">POS Admin</p>
        <p className="text-xs text-gray-500 mt-0.5">Support Panel</p>
      </div>

      <nav className="flex-1 space-y-1">
        {links.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              pathname === href
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:bg-gray-800 hover:text-white"
            }`}
          >
            <Icon size={18} />
            {label}
          </Link>
        ))}
      </nav>

      <button
        onClick={logout}
        className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-gray-400 hover:bg-gray-800 hover:text-white transition-colors w-full"
      >
        <LogOut size={18} />
        Chiqish
      </button>
    </aside>
  );
}
