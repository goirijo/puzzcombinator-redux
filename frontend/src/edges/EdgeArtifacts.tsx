// The hover "explode" overlay for an edge that carries artifacts: a count pill at the edge
// midpoint that, on hover, reveals a grid of the edge's artifacts (reusing ArtifactChip, the same
// visual as a loose artifact). The reveal is pure CSS :hover (theme.css) — both the pill and the
// grid are always rendered, so there's no React state to get stuck: the browser keeps the grid open
// while the pointer is over the pill or any chip, and closes it the moment it leaves. We feed CSS
// the midpoint, the inverse zoom (so the grid holds a fixed on-screen size), and a measured
// justified-rows width (see justifiedWidth) so the box hugs the chips.

import { useLayoutEffect, useRef, useState, type CSSProperties } from 'react'
import { EdgeLabelRenderer, useStore } from '@xyflow/react'

import type { ArtifactDTO } from '../model/graph'
import { ArtifactChip } from '../nodes/ArtifactChip'

// Target width:height of the exploded block. Higher = wider/shorter, lower = narrower/taller.
const BLOCK_ASPECT = 2.5

/**
 * Justified-rows layout, the one thing pure CSS can't do: chips keep their own widths AND the box
 * hugs them. We measure each chip, greedily pack them into rows aimed at a target row width (chosen
 * so the block ≈ BLOCK_ASPECT), and return the widest resulting row. Setting the flex container to
 * exactly that width makes flex-wrap reproduce the same packing — each row fits, and the next chip
 * that started a new row still overflows — so the box ends up snug to the widest row (narrower rows
 * just align inside it). Returns null when there's nothing to measure, when CSS falls back to
 * max-content.
 */
function justifiedWidth(chips: HTMLElement[], gap: number): number | null {
  if (chips.length === 0) return null
  // offsetWidth is rounded to an integer, so it can read ~0.5px short of a chip's true width. Pad
  // each by 1px so the computed box is never a hair narrower than the chips — which would let a chip
  // poke past the box edge or nudge a row to wrap one chip early. 1px/chip is invisible.
  const widths = chips.map((c) => c.offsetWidth + 1)
  const rowHeight = chips[0].offsetHeight + gap
  const totalWidth = widths.reduce((sum, w) => sum + w, 0) + gap * (widths.length - 1)
  // aspect ≈ rowWidth / (rows · rowHeight) and rowWidth ≈ totalWidth / rows ⇒ solve for rows.
  const rows = Math.max(1, Math.round(Math.sqrt(totalWidth / (BLOCK_ASPECT * rowHeight))))
  const target = totalWidth / rows
  let rowWidth = 0
  let widest = 0
  for (const w of widths) {
    if (rowWidth > 0 && rowWidth + gap + w > target) {
      widest = Math.max(widest, rowWidth)
      rowWidth = w
    } else {
      rowWidth = rowWidth > 0 ? rowWidth + gap + w : w
    }
  }
  return Math.max(widest, rowWidth)
}

interface EdgeArtifactsProps {
  artifacts: ArtifactDTO[]
  /** The edge midpoint, from getBezierPath — where the pill/grid anchors. */
  labelX: number
  labelY: number
}

export function EdgeArtifacts({ artifacts, labelX, labelY }: EdgeArtifactsProps) {
  // The live zoom (transform is [x, y, zoom]); the grid counter-scales by its inverse to hold a
  // fixed on-screen size at any zoom.
  const zoom = useStore((s) => s.transform[2])
  const gridRef = useRef<HTMLDivElement>(null)
  const [gridWidth, setGridWidth] = useState<number | null>(null)

  // Re-measure only when the chips' text changes (their widths depend on type + name). offsetWidth
  // is the pre-transform layout width, so measuring is unaffected by zoom (the grid's counter-scale)
  // — the justified layout is computed once in CSS pixels and just rendered scaled.
  const signature = artifacts.map((a) => `${a.type}:${a.name}`).join('|')
  useLayoutEffect(() => {
    const el = gridRef.current
    if (!el) return
    const gap = parseFloat(getComputedStyle(el).columnGap) || 0
    setGridWidth(justifiedWidth(Array.from(el.children) as HTMLElement[], gap))
  }, [signature])

  return (
    <EdgeLabelRenderer>
      {/* Dynamic values (midpoint + inverse zoom) ride in as CSS custom properties; theme.css
          composes the positioning/scale. `nodrag nopan` so hovering the overlay doesn't pan. */}
      <div
        className="edge-artifacts nodrag nopan"
        style={
          {
            '--edge-x': `${labelX}px`,
            '--edge-y': `${labelY}px`,
            '--edge-inv-zoom': 1 / zoom,
          } as CSSProperties
        }
      >
        <span className="edge-artifacts__count">{artifacts.length}</span>
        <div
          ref={gridRef}
          className="edge-artifacts__grid"
          style={gridWidth != null ? ({ '--edge-grid-width': `${gridWidth}px` } as CSSProperties) : undefined}
        >
          {artifacts.map((a) => (
            <ArtifactChip key={a.id} artifact={a} />
          ))}
        </div>
      </div>
    </EdgeLabelRenderer>
  )
}
