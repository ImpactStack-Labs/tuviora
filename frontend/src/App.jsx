import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from 'react-router-dom'

import PublicHome from './pages/PublicHome'
import PublicEvents from './pages/PublicEvents'
import PublicEventDetail from './pages/PublicEventDetail'
import AttendeeLogin from './pages/AttendeeLogin'
import OperationsPage from './pages/OperationsPage'
import AcceptInvitation from './pages/AcceptInvitation'
import SignUp from './pages/SignUp'
import VerifyEmail from './pages/VerifyEmail'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<PublicHome />} />
        <Route path="/events" element={<PublicEvents />} />
        <Route path="/events/:eventId" element={<PublicEventDetail />} />
        <Route path="/attendee/login" element={<AttendeeLogin />} />
        <Route path="/operations/*" element={<OperationsPage />} />
        <Route path="/invite" element={<AcceptInvitation />} />
        <Route path="/signup" element={<SignUp />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
