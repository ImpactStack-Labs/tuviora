import TuvioraLogo from './TuvioraLogo'

export default function AuthCard({
  as: Container = 'div',
  backLink,
  eyebrow,
  title,
  description,
  children,
  footer,
}) {
  return (
    <Container className="flex min-h-screen items-center justify-center bg-[#F7F9F5] px-5 py-12 text-[#1A3F22]">
      <div className="w-full max-w-md rounded-3xl border border-border-soft bg-white p-8 shadow-sm sm:p-10">
        {backLink}

        <div className={backLink ? 'mt-8' : ''}>
          <TuvioraLogo imageClassName="h-12 w-auto max-w-[185px]" />
        </div>

        <p className="mt-7 text-sm font-semibold uppercase tracking-widest text-[#58761B]">
          {eyebrow}
        </p>
        <h1 className="mt-2 text-3xl font-bold">{title}</h1>
        {description && (
          <p className="mt-3 leading-7 text-text-muted">{description}</p>
        )}

        {children}

        {footer && (
          <p className="mt-7 text-center text-sm text-text-muted">{footer}</p>
        )}
      </div>
    </Container>
  )
}
