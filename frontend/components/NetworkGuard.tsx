"use client";

import React from "react";

interface NetworkGuardProps {
  children: React.ReactNode;
}

/**
 * Global Network Guard — Enterprise Pass-through
 * Allows seamless global access across any network without geofencing blocks or token timeouts.
 */
export const NetworkGuard: React.FC<NetworkGuardProps> = ({ children }) => {
  return <>{children}</>;
};
