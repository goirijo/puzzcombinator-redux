// A SCRATCH-panel section: preview an artifact's *rendered* output. Rendering lives in the
// backend (an artifact's pure `render`), so this asks `/api/render` for the HTML/SVG fragment
// rather than duplicating render logic in TS. Lists every artifact in the graph (the unplaced
// pool and those riding edges); click one to pin its render into a sandboxed <iframe>. (A
// later hover-to-peek and canvas-node hover would just feed a different artifact id into the
// same render pipeline.)
//
// Why an iframe: a fragment's `styles` are global-ish CSS that would otherwise collide with
// the editor's own styles. `srcdoc` sandboxes them — and is also how the binder composes a
// standalone document, so the preview matches the real output.

import { useEffect, useRef, useState } from 'react'
import { renderArtifact, type RenderedArtifactDTO } from '../../model/api'
import type { ArtifactDTO } from '../../model/graph'
import { isLooseArtifactNode } from '../../model/flow'
import { useGraphStore } from '../../shell/graphStore'

/** Wrap a rendered fragment in a minimal standalone document for the preview iframe. HTML and
 *  inline-SVG fragments both embed straight into the body; the styles ride in the head. */
function previewDocument(rendered: RenderedArtifactDTO): string {
  return `<!doctype html><html><head><meta charset="utf-8"><style>${rendered.styles}</style></head><body>${rendered.markup}</body></html>`
}

export function PreviewSection() {
  // Every artifact in the graph: the unplaced pool (loose-artifact nodes) plus those riding
  // edges (each edge's `content`). Both shapes live in the store already, so previewing one is
  // the same render call regardless of where it sits.
  const artifacts = useGraphStore((s) => [
    ...s.nodes.filter(isLooseArtifactNode).map((n) => n.data.artifact),
    ...s.edges.flatMap((e) => e.data?.content ?? []),
  ])
  const [pinnedId, setPinnedId] = useState<string | null>(null)
  const [rendered, setRendered] = useState<RenderedArtifactDTO | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Memo cache: a render is a pure function of the artifact's value, so it never goes stale
  // until the artifact is edited. Keying by the full envelope means an edit misses the cache
  // (good) while re-viewing the same artifact is free — one fetch per distinct value.
  const cache = useRef(new Map<string, RenderedArtifactDTO>())

  const active = artifacts.find((a) => a.id === pinnedId) ?? null

  useEffect(() => {
    if (!active) {
      setRendered(null)
      setError(null)
      return
    }
    const key = JSON.stringify(active)
    const hit = cache.current.get(key)
    if (hit) {
      setRendered(hit)
      setError(null)
      return
    }
    let cancelled = false
    renderArtifact(active)
      .then((r) => {
        cache.current.set(key, r)
        if (!cancelled) {
          setRendered(r)
          setError(null)
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setRendered(null)
          setError(e instanceof Error ? e.message : String(e))
        }
      })
    return () => {
      cancelled = true
    }
  }, [active])

  return (
    <section className="view-panel__section">
      <h3 className="inspector__heading">Preview</h3>
      {artifacts.length === 0 ? (
        <p className="preview__empty">No artifacts to preview.</p>
      ) : (
        <ul className="preview__list">
          {artifacts.map((a: ArtifactDTO) => (
            <li key={a.id}>
              <button
                type="button"
                className="ghost-btn preview__item"
                aria-pressed={a.id === pinnedId}
                onClick={() => setPinnedId(a.id)}
              >
                <span className="preview__item-name">{a.name}</span>
                <span className="preview__item-type">{a.type}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {error && <p className="preview__error">{error}</p>}
      {rendered && (
        <iframe
          className="preview__frame"
          title="Artifact preview"
          sandbox=""
          srcDoc={previewDocument(rendered)}
        />
      )}
    </section>
  )
}
