import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import './App.css';

const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Transactions = lazy(() => import('./pages/Transactions'));
const UploadStatement = lazy(() => import('./pages/UploadStatement'));
const Budgets = lazy(() => import('./pages/Budgets'));
const BudgetRecommendations = lazy(() => import('./pages/BudgetRecommendations'));
const SavingsGoals = lazy(() => import('./pages/SavingsGoals'));
const Insights = lazy(() => import('./pages/Insights'));
const NeedsReview = lazy(() => import('./pages/NeedsReview'));
const Friends = lazy(() => import('./pages/Friends'));

function App() {
  return (
    <Router>
      <AuthProvider>
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
              path="/needs-review"
              element={
                <ProtectedRoute>
                  <NeedsReview />
                </ProtectedRoute>
              }
            />
            <Route
              path="/budgets"
              element={
                <ProtectedRoute>
                  <Budgets />
                </ProtectedRoute>
              }
            />
            <Route
              path="/recommendations"
              element={
                <ProtectedRoute>
                  <BudgetRecommendations />
                </ProtectedRoute>
              }
            />
            <Route
              path="/savings-goals"
              element={
                <ProtectedRoute>
                  <SavingsGoals />
                </ProtectedRoute>
              }
            />
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
      </AuthProvider>
    </Router>
  );
}

export default App;
