"use client";

import React, { createContext, useContext, useState } from "react";

export interface ToastMessage {
  id: string;
  type: "info" | "success" | "error" | "warning";
  text: string;
}

interface NotificationContextType {
  toasts: ToastMessage[];
  addToast: (type: "info" | "success" | "error" | "warning", text: string) => void;
  removeToast: (id: string) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export default function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = (type: "info" | "success" | "error" | "warning", text: string) => {
    const id = Math.random().toString(36).substring(2);
    setToasts((prev) => [...prev, { id, type, text }]);
    setTimeout(() => removeToast(id), 5000); // Auto remove after 5 seconds
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  };

  return (
    <NotificationContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      {/* Toast Alert overlay listing */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            onClick={() => removeToast(toast.id)}
            className={`cursor-pointer p-4 rounded-lg border text-sm shadow-lg flex justify-between items-center transition-all duration-300 ${
              toast.type === "success"
                ? "bg-emerald-950 border-emerald-800 text-emerald-200"
                : toast.type === "error"
                ? "bg-destructive border-red-800 text-red-200"
                : toast.type === "warning"
                ? "bg-amber-950 border-amber-800 text-amber-200"
                : "bg-zinc-900 border-zinc-800 text-zinc-200"
            }`}
          >
            <span>{toast.text}</span>
            <button className="text-xs opacity-50 hover:opacity-100 ml-4">✕</button>
          </div>
        ))}
      </div>
    </NotificationContext.Provider>
  );
}

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error("useNotifications must be used within a NotificationProvider");
  }
  return context;
};
export { NotificationProvider };
