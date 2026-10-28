import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { AboutPage } from './pages/AboutPage'
import { ExercisePage } from './pages/ExercisePage'
import { ExercisesPage } from './pages/ExercisesPage'
import { HomePage } from './pages/HomePage'
import { LanguagesPage } from './pages/LanguagesPage'
import { LoginPage } from './pages/LoginPage'
import { ProfilePage } from './pages/ProfilePage'
import { RegisterPage } from './pages/RegisterPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="practice" element={<LanguagesPage />} />
        <Route path="practice/:sourceCode/:targetCode/exercises" element={<ExercisesPage />} />
        <Route path="practice/:sourceCode/:targetCode/exercises/:exerciseId" element={<ExercisePage />} />
        <Route path="languages" element={<Navigate to="/practice" replace />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="profile" element={<ProfilePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
