import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { UIProvider } from './context/UIContext';
import ConfirmModal from './components/ui/ConfirmModal';
import ProtectedRoute from './components/layout/ProtectedRoute';
import ToastHost from './components/ui/ToastHost';
import './styles/App.css';

const Login = lazy(() => import('./features/auth/Login'));
const Register = lazy(() => import('./features/auth/Register'));
const Dashboard = lazy(() => import('./features/dashboard/Dashboard'));
const Transactions = lazy(() => import('./features/transactions/Transactions'));
const UploadStatement = lazy(() => import('./features/upload/UploadStatement'));
const AIInsights = lazy(() => import('./features/ai-insights/AIInsights'));
const Categories = lazy(() => import('./features/categories/Categories'));
const CategoryBreakdown = lazy(() => import('./features/categories/CategoryBreakdown'));
const Friends = lazy(() => import('./features/friends/Friends'));

function App() {
  return (
    <Router>
      <AuthProvider>
        <UIProvider>
          <Suspense fallback={<div className="app-loading">Loading...</div>}>
            <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Protected Routes */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/transactions"
              element={
                <ProtectedRoute>
                  <Transactions />
                </ProtectedRoute>
              }
            />
            <Route
              path="/upload"
              element={
                <ProtectedRoute>
                  <UploadStatement />
                </ProtectedRoute>
              }
            />
            <Route
              path="/categories"
              element={
                <ProtectedRoute>
                  <Categories />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard/category-analytics"
              element={
                <ProtectedRoute>
                  <CategoryBreakdown />
                </ProtectedRoute>
              }
            />
            <Route
              path="/friends"
              element={
                <ProtectedRoute>
                  <Friends />
                </ProtectedRoute>
              }
            />
            <Route
              path="/ai-insights"
              element={
                <ProtectedRoute>
                  <AIInsights />
                </ProtectedRoute>
              }
            />
            {/* Redirect */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </Suspense>
          <ToastHost />
          <ConfirmModal />
        </UIProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
