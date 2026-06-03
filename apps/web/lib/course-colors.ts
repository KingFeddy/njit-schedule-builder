const PALETTE = [
  '#1E3A5F', // deep navy
  '#1A3A2A', // deep forest
  '#3A1A2A', // deep plum
  '#3A2A1A', // deep bronze
  '#1A2A3A', // deep slate
  '#2A1A3A', // deep violet
]

function hashCode(str: string): number {
  let h = 0
  for (let i = 0; i < str.length; i++) h = (Math.imul(31, h) + str.charCodeAt(i)) | 0
  return Math.abs(h)
}

export function courseColor(code: string): string {
  return PALETTE[hashCode(code) % PALETTE.length]
}
