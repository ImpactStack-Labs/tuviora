import { LockKeyhole, LogIn } from 'lucide-react'

export default function CredentialsForm({
  username,
  onUsernameChange,
  password,
  onPasswordChange,
  error,
  loading,
  onSubmit,
  submitLabel = 'Sign in',
  submittingLabel = 'Signing in...',
}) {
  return (
    <form onSubmit={onSubmit} className="mt-8 space-y-5">
      <div>
        <label htmlFor="auth-username" className="font-semibold text-[#1A3F22]">
          Username
        </label>
        <input
          id="auth-username"
          type="text"
          autoComplete="username"
          value={username}
          onChange={onUsernameChange}
          required
          className="mt-2 w-full rounded-xl border border-border-soft px-4 py-3 outline-none focus:border-[#58761B]"
        />
      </div>

      <div>
        <label htmlFor="auth-password" className="font-semibold text-[#1A3F22]">
          Password
        </label>
        <div className="relative mt-2">
          <LockKeyhole
            size={19}
            className="absolute left-4 top-3.5 text-[#718072]"
          />
          <input
            id="auth-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={onPasswordChange}
            required
            className="w-full rounded-xl border border-border-soft py-3 pl-12 pr-4 outline-none focus:border-[#58761B]"
          />
        </div>
      </div>

      {error && (
        <p role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={loading}
        className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#1A3F22] px-5 py-3 font-semibold text-white transition hover:bg-[#31563A] disabled:opacity-60"
      >
        <LogIn size={19} />
        {loading ? submittingLabel : submitLabel}
      </button>
    </form>
  )
}
