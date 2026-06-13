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
const Budgets = lazy(() => import('./pages/Budgets'));
const Investments = lazy(() => import('./pages/Investments'));
const FinancialHealth = lazy(() => import('./pages/FinancialHealth'));
const Forecast = lazy(() => import('./pages/Forecast'));
const Subscriptions = lazy(() => import('./pages/Subscriptions'));
const Insights = lazy(() => import('./pages/Insights'));
const Categories = lazy(() => import('./pages/Categories'));
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
              path="/friends"
              element={
                <ProtectedRoute>
                  <Friends />
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
            <Route path="/needs-review" element={<Navigate to="/categories" replace />} />
            <Route
              path="/budgets"
              element={
                <ProtectedRoute>
                  <Budgets />
                </ProtectedRoute>
              }
            />
            <Route path="/recommendations" element={<Navigate to="/insights" replace />} />
            <Route path="/savings-goals" element={<Navigate to="/investments" replace />} />
            <Route path="/savings" element={<Navigate to="/investments" replace />} />
            <Route
              path="/investments"
              element={
                <ProtectedRoute>
                  <Investments />
                </ProtectedRoute>
              }
            />
            <Route
              path="/financial-health"
              element={
                <ProtectedRoute>
                  <FinancialHealth />
                </ProtectedRoute>
              }
            />
            <Route
              path="/forecast"
              element={
                <ProtectedRoute>
                  <Forecast />
                </ProtectedRoute>
              }
            />
            <Route
              path="/subscriptions"
              element={
                <ProtectedRoute>
                  <Subscriptions />
                </ProtectedRoute>
              }
            />
            <Route path="/assistant" element={<Navigate to="/dashboard" replace />} />
            <Route
              path="/insights"
              element={
                <ProtectedRoute>
                  <Insights />
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
