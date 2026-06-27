// A node with no label falls back to showing its id. Ids are now opaque uuids, which would
// stretch the node, so the fallback shows just a 6-char prefix — like a shortened git commit
// hash, no ellipsis (the full id stays on the node's title for hover, and in the inspector).
// Short ids — e.g. the backend's readable `nN` scheme — are shorter than the cap, so they show
// in full. Kept in its own file so HuntNode.tsx exports only the component (react-refresh rule).

export function shortId(id: string): string {
  return id.slice(0, 6)
}
