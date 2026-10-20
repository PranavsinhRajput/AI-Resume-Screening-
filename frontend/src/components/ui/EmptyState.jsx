export default function EmptyState({ icon: Icon, title, children, action }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-line bg-panel px-6 py-10 text-center">
      {Icon && <Icon className="h-8 w-8 text-accent" aria-hidden="true" />}
      <p className="font-semibold text-text">{title}</p>
      {children && <div className="max-w-md text-sm text-muted">{children}</div>}
      {action}
    </div>
  )
}
