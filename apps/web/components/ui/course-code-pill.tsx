export function CourseCodePill({ code }: { code: string }) {
  return (
    <span className="font-mono text-sm text-text px-2 py-0.5 rounded-md bg-surface-2 border border-border">
      {code}
    </span>
  )
}
