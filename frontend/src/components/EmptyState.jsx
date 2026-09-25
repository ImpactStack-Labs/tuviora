export default function EmptyState({
  icon: Icon,
  title,
  description,
  as: Heading = 'h3',
  size = 'default',
  bordered = true,
}) {
  const large = size === 'lg'

  const chrome = bordered
    ? `rounded-2xl border border-border-soft bg-white text-center ${large ? 'p-12' : 'p-10'}`
    : 'flex min-h-56 flex-col items-center justify-center text-center'

  return (
    <div className={chrome}>
      <Icon size={large ? 40 : 36} className="mx-auto text-[#58761B]" />
      <Heading className={`mt-4 font-bold ${large ? 'text-2xl' : 'text-lg'}`}>
        {title}
      </Heading>
      {description && (
        <p className={`mt-2 text-text-muted ${large ? '' : 'text-sm'}`}>
          {description}
        </p>
      )}
    </div>
  )
}
