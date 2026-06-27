// Pure helpers for undo-history granularity, kept out of store.ts so they're independently
// testable (and easy to move/replace as the editor evolves). `graphSignature` decides what
// counts as a meaningful change; `leadingDebounce` decides how a burst of changes collapses
// into one history step. See store.ts for how zundo's `temporal` middleware uses them.

import { isLooseArtifactNode, type CanvasGraph } from '../model/flow'

/**
 * A signature of the *meaningful* graph state. It deliberately ignores volatile React Flow
 * flags (`selected`, `dragging`, measured dimensions) and rounds positions, so two states
 * with the same signature differ only in ways not worth an undo step (e.g. a selection
 * click, or sub-pixel drag jitter). Equal signatures ⇒ no new history entry. Hunt nodes
 * contribute their editable fields; loose-artifact nodes contribute their artifact id (their
 * payload isn't editable on the canvas yet).
 */
export function graphSignature({ nodes, edges }: CanvasGraph): string {
  const n = nodes
    .map((x) => {
      const at = `${x.id}@${Math.round(x.position.x)},${Math.round(x.position.y)}`
      return isLooseArtifactNode(x)
        ? `${at}:art:${x.data.artifact.id}`
        : `${at}:${x.data.label}|${x.data.action}|${x.data.notes}`
    })
    .join(';')
  const e = edges.map((x) => `${x.id}:${x.source}->${x.target}`).join(';')
  return `${n}#${e}`
}

/**
 * Leading-edge debounce: fire `fn` on the *first* call of a burst (with that call's args),
 * then suppress further calls until `ms` of quiet. Used so a burst of edits records the
 * state from *before* the burst (the correct undo target); a trailing debounce would wrongly
 * capture a mid-burst state.
 */
export function leadingDebounce<A extends unknown[]>(fn: (...args: A) => void, ms: number) {
  let active = false
  let timer: ReturnType<typeof setTimeout> | undefined
  return (...args: A) => {
    if (!active) fn(...args)
    active = true
    clearTimeout(timer)
    timer = setTimeout(() => {
      active = false
    }, ms)
  }
}
