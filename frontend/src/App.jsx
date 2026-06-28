import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { UIProvider } from './context/UIContext';
import ConfirmModal from './components/ConfirmModal';
import ProtectedRoute from './components/ProtectedRoute';
import ToastHost from './components/ToastHost';
import './App.css';

const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Transactions = lazy(() => import('./pages/Transactions'));
const UploadStatement = lazy(() => import('./pages/UploadStatement'));
const AIInsights = lazy(() => import('./pages/AIInsights'));
const Categories = lazy(() => import('./pages/Categories'));
const CategoryBreakdown = lazy(() => import('./pages/CategoryBreakdown'));
const Friends = lazy(() => import('./pages/Friends'));

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
            <Route path="/merchants" element={<Navigate to="/dashboard" replace />} />
            <Route path="/needs-review" element={<Navigate to="/categories" replace />} />
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
            <Route path="/category-breakdown" element={<Navigate to="/dashboard/category-analytics" replace />} />
            <Route path="/financial-health" element={<Navigate to="/ai-insights" replace />} />
            <Route path="/insights" element={<Navigate to="/ai-insights" replace />} />

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
