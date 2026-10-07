"use client";

import React, { Suspense } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { FileText, Wrench, FolderOpen, Settings, ShieldAlert, Trash2 } from "lucide-react";

interface NavbarProps {
  overallConfidence?: number;
  overallConfidenceLevel?: "red" | "yellow" | "green";
  onDeleteData?: () => void;
}

function NavbarContent({
  overallConfidence,
  overallConfidenceLevel,
  onDeleteData
}: NavbarProps) {
  const pathname = usePathname() || "";

  const navLinks = [
    { href: "/", label: "Dashboard", icon: FileText },
    { href: "/tools", label: "Tools", icon: Wrench },
    { href: "/documents", label: "Documents", icon: FolderOpen },
    { href: "/settings", label: "Settings", icon: Settings },
  ];

  const confBg =
    overallConfidenceLevel === "green"
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : overallConfidenceLevel === "yellow"
      ? "bg-amber-50 text-amber-700 border-amber-200"
      : "bg-rose-50 text-rose-700 border-rose-200";

  return (
    <header className="sticky top-0 z-50 bg-slate-900 border-b border-slate-800 text-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Brand Logo */}
        <div className="flex items-center space-x-3">
          <Link href="/" className="flex items-center space-x-2 group">
            <div className="w-8 h-8 rounded bg-teal-600 flex items-center justify-center font-bold text-white tracking-wider text-sm shadow-sm group-hover:bg-teal-500 transition">
              SY
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight text-slate-100">SYNOPSIZE</span>
              <span className="hidden sm:inline-block ml-2 text-xs font-medium px-2 py-0.5 rounded bg-slate-800 text-teal-400 border border-slate-700">
                Universal Engine
              </span>
            </div>
          </Link>
        </div>

        {/* Center Navigation Links */}
        <nav className="flex space-x-1 sm:space-x-2">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href));
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center space-x-2 px-3 py-1.5 rounded-md text-sm font-medium transition ${
                  isActive
                    ? "bg-slate-800 text-teal-400 border border-slate-700 shadow-inner"
                    : "text-slate-300 hover:text-white hover:bg-slate-800/60"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{link.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Right Action & Confidence Score Badge */}
        <div className="flex items-center space-x-3">
          {overallConfidence !== undefined && (
            <div className={`flex items-center space-x-1.5 px-3 py-1 rounded text-xs font-semibold border ${confBg}`}>
              <span className="w-2 h-2 rounded-full bg-current" />
              <span>Score: {(overallConfidence * 100).toFixed(0)}%</span>
            </div>
          )}

          {onDeleteData && (
            <button
              onClick={onDeleteData}
              title="Delete my data now"
              className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded border border-rose-800/60 bg-rose-950/40 text-rose-300 hover:bg-rose-900/50 hover:text-rose-100 text-xs font-medium transition"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Delete Data</span>
            </button>
          )}
        </div>

      </div>
    </header>
  );
}

export default function Navbar(props: NavbarProps) {
  return (
    <Suspense fallback={<header className="sticky top-0 z-50 bg-slate-900 border-b border-slate-800 text-white shadow-sm h-16" />}>
      <NavbarContent {...props} />
    </Suspense>
  );
}

