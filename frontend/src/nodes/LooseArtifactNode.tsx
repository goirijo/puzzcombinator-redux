// A loose (unplaced) artifact drawn on the canvas. Deliberately unlike HuntNode: it renders
// NO handles, so React Flow can't start or end a connection on it — a loose artifact is never
// wired, it meets edges by being dragged onto them (a later phase). Its own `.loose-node`
// styling (distinct shape/color + a type tag) makes it easy to tell apart from graph nodes.
// Purely presentational; all colors/sizes come from theme.css.

import { type NodeProps } from '@xyflow/react'
import type { LooseArtifactFlowNode } from '../model/flow'

export function LooseArtifactNode({ data }: NodeProps<LooseArtifactFlowNode>) {
  const { artifact } = data
  // Render ONLY what every artifact has — its type and name. The node never reaches into the
  // type-specific `payload` (text/image/svg/qr/…), so one node works identically for every
  // artifact kind. Showing an artifact's actual contents is a separate concern (a future
  // preview), not this canvas chip's job.
  return (
    <div className="artifact-node">
      <span className="artifact-node__tag">{artifact.type}</span>
      <div className="artifact-node__body">{artifact.name}</div>
    </div>
  )
}
