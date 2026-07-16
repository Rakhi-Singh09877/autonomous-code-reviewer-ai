"use client";

import React, { createContext, useContext, useState } from "react";
import { User } from "../domain/entities";

interface SessionContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: () => void;
  logout: () => void;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export default function SessionProvider({ children }: { children: React.ReactNode }) {
  // Placeholder mock user config (unauthenticated by default)
  const [user] = useState<User | null>(null);

  const login = () => {
    console.log("Mock login triggered");
  };

  const logout = () => {
    console.log("Mock logout triggered");
  };

  return (
    <SessionContext.Provider value={{ user, isAuthenticated: !!user, login, logout }}>
      {children}
    </SessionContext.Provider>
  );
}

export const useSession = () => {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return context;
};

export const useCurrentUser = () => {
  return useSession().user;
};

export const usePermissions = () => {
  const user = useCurrentUser();
  return {
    canTriggerAnalysis: user?.roles.includes("admin") ?? false,
    canDownloadReports: !!user,
  };
};
