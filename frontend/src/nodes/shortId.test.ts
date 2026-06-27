import { describe, expect, it } from 'vitest'

import { shortId } from './shortId'

describe('shortId', () => {
  it('passes short ids (like the backend nN scheme) through in full', () => {
    expect(shortId('n3')).toBe('n3')
    expect(shortId('start')).toBe('start')
  })

  it('shows just a 6-char prefix of a long opaque uuid (git-hash style, no ellipsis)', () => {
    expect(shortId('a3f2c1e8-1234-5678-9abc-def012345678')).toBe('a3f2c1')
  })
})
