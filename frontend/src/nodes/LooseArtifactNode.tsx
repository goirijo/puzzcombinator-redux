// A loose (unplaced) artifact drawn on the canvas. Deliberately unlike HuntNode: it renders
// NO handles, so React Flow can't start or end a connection on it — a loose artifact is never
// wired, it meets edges by being dragged onto them. The visual is ArtifactChip (shared with the
// edge "explode" grid), so a pooled artifact and an artifact revealed on an edge look identical.

import { type NodeProps } from '@xyflow/react'
import type { LooseArtifactFlowNode } from '../model/flow'
import { ArtifactChip } from './ArtifactChip'

export function LooseArtifactNode({ data }: NodeProps<LooseArtifactFlowNode>) {
  return <ArtifactChip artifact={data.artifact} />
}
