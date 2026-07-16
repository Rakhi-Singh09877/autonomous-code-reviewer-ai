"use client";

import React, { createContext, useContext, useState } from "react";

interface PaletteContextType {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  toggle: () => void;
}

const PaletteContext = createContext<PaletteContextType | undefined>(undefined);

export default function PaletteProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);

  const toggle = () => setIsOpen((prev) => !prev);

  return (
    <PaletteContext.Provider value={{ isOpen, setIsOpen, toggle }}>
      {children}
      {isOpen && (
        <div 
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
        >
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 max-w-lg w-full shadow-2xl">
            <h2 className="text-lg font-bold mb-4">Command Palette (Placeholder)</h2>
            <p className="text-sm text-zinc-400 mb-4">
              Press <kbd className="bg-zinc-800 px-2 py-1 rounded text-xs">Esc</kbd> to close.
            </p>
            <button 
              onClick={() => setIsOpen(false)}
              className="btn-primary px-4 py-2 rounded text-sm w-full"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </PaletteContext.Provider>
  );
}

export const usePalette = () => {
  const context = useContext(PaletteContext);
  if (!context) {
    throw new Error("usePalette must be used within a PaletteProvider");
  }
  return context;
};
