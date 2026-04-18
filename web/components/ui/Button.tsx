// Base button component
import type { ButtonHTMLAttributes } from 'react';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'ghost';
};

export function Button({ variant = 'primary', className = '', ...rest }: Props) {
  const base =
    'inline-flex items-center justify-center rounded-pill px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50';
  const styles =
    variant === 'primary'
      ? 'bg-neutral-900 text-white hover:bg-neutral-800'
      : 'border border-neutral-300 text-neutral-800 hover:border-neutral-400';
  return <button type="button" className={`${base} ${styles} ${className}`} {...rest} />;
}
