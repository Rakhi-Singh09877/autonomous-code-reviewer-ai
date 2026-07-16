"use client";

import React, { createContext, useContext, useEffect } from "react";

interface ShortcutContextType {
  registerShortcut: (keys: string, callback: () => void) => () => void;
}

const ShortcutContext = createContext<ShortcutContextType | undefined>(undefined);

export default function ShortcutProvider({ children }: { children: React.ReactNode }) {
  const registerShortcut = (keys: string, callback: () => void) => {
    console.log(`Registered keyboard shortcut placeholder: ${keys}`, callback);
    return () => {
      console.log(`Unregistered keyboard shortcut placeholder: ${keys}`);
    };
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Mock listener checking key bounds
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        console.log("Global command palette shortcut (Ctrl+K) intercepted");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <ShortcutContext.Provider value={{ registerShortcut }}>
      {children}
    </ShortcutContext.Provider>
  );
}

export const useShortcuts = () => {
  const context = useContext(ShortcutContext);
  if (!context) {
    throw new Error("useShortcuts must be used within a ShortcutProvider");
  }
  return context;
};
