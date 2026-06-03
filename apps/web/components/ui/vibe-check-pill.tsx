export function VibeCheckPill({ tag }: { tag: string }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-mono text-muted bg-surface-2 border border-border">
      {tag}
    </span>
  )
}
