import { Navigate, useLocation } from 'react-router-dom';

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('access_token');
  const location = useLocation();

  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
