import type { ButtonHTMLAttributes, ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-lg border border-line bg-white ${className}`}>{children}</section>;
}

export function CardHeader({ title, aside }: { title: string; aside?: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
      <h2 className="text-sm font-semibold">{title}</h2>
      {aside}
    </div>
  );
}

type ButtonKind = "primary" | "secondary" | "danger";

const BUTTON_STYLES: Record<ButtonKind, string> = {
  primary: "bg-grass text-white hover:bg-green-800 disabled:bg-green-300",
  secondary: "border border-line bg-white text-ink hover:bg-gray-50 disabled:text-muted",
  danger: "border border-red-200 bg-white text-red-700 hover:bg-red-50",
};

export function Button({
  kind = "secondary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { kind?: ButtonKind }) {
  return (
    <button
      type="button"
      className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-4 text-sm font-medium transition-colors disabled:cursor-not-allowed ${BUTTON_STYLES[kind]} ${className}`}
      {...props}
    />
  );
}

export function LinkButton({ href, kind = "secondary", children }: { href: string; kind?: ButtonKind; children: ReactNode }) {
  return (
    <a
      href={href}
      className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-4 text-sm font-medium transition-colors ${BUTTON_STYLES[kind]}`}
    >
      {children}
    </a>
  );
}

export function SampleBadge() {
  return (
    <span
      className="rounded bg-miss-soft px-1.5 py-0.5 text-[11px] font-medium text-miss"
      title="Simulated sample data, not real flights"
    >
      sample
    </span>
  );
}

export function Notice({ tone = "info", children }: { tone?: "info" | "error"; children: ReactNode }) {
  const style = tone === "error" ? "border-red-200 bg-red-50 text-red-800" : "border-line bg-white text-muted";
  return (
    <p role={tone === "error" ? "alert" : undefined} className={`rounded-md border px-3 py-2 text-sm ${style}`}>
      {children}
    </p>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <div className="px-4 py-3">
      <div className="text-xs text-muted">{label}</div>
      <div className="num mt-0.5 text-xl font-semibold">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-muted">{hint}</div>}
    </div>
  );
}

export function Loading() {
  return <p className="py-10 text-center text-sm text-muted">Loading…</p>;
}
