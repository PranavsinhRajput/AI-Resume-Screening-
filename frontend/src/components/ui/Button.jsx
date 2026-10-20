import clsx from 'clsx'
import Spinner from './Spinner.jsx'

const VARIANTS = {
  primary:
    'bg-accent text-harvest-orange-950 shadow-button hover:bg-accent-strong active:bg-accent-strong font-semibold',
  secondary: 'bg-panel text-text border border-line hover:bg-elevated',
  ghost: 'bg-transparent text-text hover:bg-elevated',
  danger:
    'bg-red-600 text-white hover:bg-red-700 dark:bg-red-500 dark:text-black dark:hover:bg-red-400 font-semibold',
}

const SIZES = {
  sm: 'min-h-11 md:min-h-9 px-3 text-sm',
  md: 'min-h-11 px-4 text-sm',
  icon: 'h-11 w-11 justify-center',
}

/**
 * @param {{variant?: 'primary'|'secondary'|'ghost'|'danger', size?: 'sm'|'md'|'icon', loading?: boolean} & React.ButtonHTMLAttributes<HTMLButtonElement>} props
 */
export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  className,
  children,
  disabled,
  type = 'button',
  ...rest
}) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={clsx(
        'inline-flex items-center gap-2 rounded-xl transition-colors disabled:cursor-not-allowed disabled:opacity-60',
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...rest}
    >
      {loading && <Spinner className="h-4 w-4" />}
      {children}
    </button>
  )
}
