"use client";

import React, { useState, useEffect } from "react";
import { useTheme } from "next-themes";
import {
  LayoutDashboard,
  Terminal,
  FileCode,
  Settings,
  Sun,
  Moon,
  Menu,
  X,
  Activity,
  Database,
  Brain,
  Cpu,
  Search,
} from "lucide-react";
import { cn } from "../../lib";

interface WorkspaceShellProps {
  children: React.ReactNode;
}

export function WorkspaceShell({ children }: WorkspaceShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // Fix hydration mismatch issues for next-themes
  useEffect(() => {
    setMounted(true);
  }, []);

  const navItems = [
    { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { label: "Live Analysis", href: "/dashboard/analysis/placeholder", icon: Terminal },
    { label: "Report Viewer", href: "/dashboard/reports/placeholder", icon: FileCode },
    { label: "Settings", href: "/settings", icon: Settings },
  ];

  const healthIndicators = [
    { label: "API Gateway", status: "online", icon: Activity },
    { label: "Redis Broker", status: "online", icon: Cpu },
    { label: "Database", status: "online", icon: Database },
    { label: "LLM Agent", status: "online", icon: Brain },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-zinc-950 text-zinc-100 font-sans selection:bg-cyan-500/30">
      {/* 1. Header (Top Navigation) */}
      <header className="sticky top-0 z-40 w-full border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur-md px-4 h-14 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-md hover:bg-zinc-800 text-zinc-400 focus:outline-none"
            aria-label="Toggle mobile menu"
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center font-bold text-xs text-white">
              A
            </div>
            <span className="font-semibold text-sm tracking-tight hidden sm:inline-block font-sans">
              Autonomous Reviewer AI
            </span>
          </div>

          <div className="hidden md:flex items-center gap-4 ml-8 border-l border-zinc-800 pl-8">
            {healthIndicators.map((item, idx) => (
              <div 
                key={idx} 
                className="flex items-center gap-1.5 text-xs text-zinc-400"
                title={`${item.label}: ${item.status}`}
              >
                <item.icon size={14} className="text-zinc-500" />
                <span className="hidden lg:inline">{item.label}</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              </div>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Quick search input mock */}
          <div className="relative hidden md:block w-48 lg:w-64">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-zinc-500" />
            <input
              type="search"
              placeholder="Search workspaces... (Ctrl+K)"
              className="w-full bg-zinc-900 border border-zinc-800 rounded-md py-1.5 pl-9 pr-3 text-xs text-zinc-300 placeholder-zinc-500 focus:outline-none focus:border-cyan-500/50"
              readOnly
            />
          </div>

          {/* Theme switcher */}
          {mounted && (
            <button
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className="p-2 rounded-md hover:bg-zinc-800 text-zinc-400 focus:outline-none focus:ring-2 focus:ring-cyan-500/40"
              aria-label="Toggle Theme"
            >
              {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          )}

          {/* User profile avatar placeholder */}
          <div className="w-8 h-8 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center font-semibold text-xs text-zinc-300 cursor-pointer">
            JD
          </div>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* 2. Collapsible Sidebar (Desktop) */}
        <aside
          className={cn(
            "hidden md:flex flex-col border-r border-zinc-800/80 bg-zinc-950/50 transition-all duration-300",
            sidebarOpen ? "w-64" : "w-16"
          )}
        >
          <div className="flex-1 py-4 flex flex-col justify-between">
            <nav className="space-y-1 px-2">
              {navItems.map((item, idx) => (
                <a
                  key={idx}
                  href={item.href}
                  className="flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 transition-colors group"
                >
                  <item.icon size={18} className="text-zinc-400 group-hover:text-cyan-400 transition-colors shrink-0" />
                  {sidebarOpen && <span>{item.label}</span>}
                </a>
              ))}
            </nav>

            <div className="px-3">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="w-full text-left py-2 text-xs text-zinc-400 hover:text-zinc-300 hidden md:block"
              >
                {sidebarOpen ? "◀ Collapse Sidebar" : "▶"}
              </button>
            </div>
          </div>
        </aside>

        {/* 3. Mobile Navigation Drawer Overlay */}
        {mobileMenuOpen && (
          <div 
            className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm md:hidden"
            onClick={() => setMobileMenuOpen(false)}
          >
            <aside 
              className="absolute left-0 top-0 bottom-0 w-64 bg-zinc-950 border-r border-zinc-800 p-4 flex flex-col justify-between"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="space-y-6">
                <div className="flex items-center justify-between border-b border-zinc-900 pb-4">
                  <span className="font-semibold">Menu Navigation</span>
                  <button onClick={() => setMobileMenuOpen(false)}>
                    <X size={18} />
                  </button>
                </div>
                <nav className="space-y-1">
                  {navItems.map((item, idx) => (
                    <a
                      key={idx}
                      href={item.href}
                      onClick={() => setMobileMenuOpen(false)}
                      className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900"
                    >
                      <item.icon size={18} className="text-zinc-400" />
                      <span>{item.label}</span>
                    </a>
                  ))}
                </nav>
              </div>

              <div className="border-t border-zinc-900 pt-4 flex flex-col gap-2">
                {healthIndicators.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between text-xs text-zinc-500">
                    <span className="flex items-center gap-2">
                      <item.icon size={12} />
                      {item.label}
                    </span>
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  </div>
                ))}
              </div>
            </aside>
          </div>
        )}

        {/* 4. Main Content Area */}
        <main className="flex-1 overflow-y-auto bg-zinc-950 p-6 md:p-8">
          <div className="max-w-7xl mx-auto space-y-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
export default WorkspaceShell;
