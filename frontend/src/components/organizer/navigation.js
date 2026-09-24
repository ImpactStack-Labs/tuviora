import {
  LayoutDashboard,
  CalendarDays,
  ClipboardCheck,
  Users,
  ScanLine,
  CreditCard,
  Radio,
  MessageSquare,
  BarChart3,
} from 'lucide-react'

export const navigation = [
  { name: 'Overview', path: '', icon: LayoutDashboard },
  { name: 'My Events', path: 'events', icon: CalendarDays },
  { name: 'Event Readiness', path: 'readiness', icon: ClipboardCheck },
  { name: 'Event Team', path: 'team', icon: Users },
  { name: 'Registration', path: 'registration', icon: Users },
  { name: 'Attendance', path: 'attendance', icon: ScanLine },
  { name: 'Payments', path: 'payments', icon: CreditCard },
  { name: 'Live Operations', path: 'live', icon: Radio },
  { name: 'Communications', path: 'communications', icon: MessageSquare },
  { name: 'Feedback', path: 'feedback', icon: MessageSquare },
  { name: 'Analytics', path: 'analytics', icon: BarChart3 },
]
