// src/components/ProtectedRoute.tsx
import { ReactElement } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { isAuthenticated } from "../auth";

type Props = {
  children: ReactElement;
};

export function ProtectedRoute({ children }: Props) {
  const location = useLocation();

  if (!isAuthenticated()) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}
