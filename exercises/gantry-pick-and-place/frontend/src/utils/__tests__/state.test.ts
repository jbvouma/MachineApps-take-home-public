import { describe, it, expect } from 'vitest'
import { classifyState, humanizeState } from '../state'

describe('humanizeState', () => {
  it('strips the group prefix and title-cases sequence states', () => {
    expect(humanizeState('Seq_movingToCube')).toBe('Moving To Cube')
  })

  it('title-cases simple states', () => {
    expect(humanizeState('ready')).toBe('Ready')
    expect(humanizeState('fault')).toBe('Fault')
  })

  it('handles empty input', () => {
    expect(humanizeState('')).toBe('Unknown')
  })
})

describe('classifyState', () => {
  it('classifies known states', () => {
    expect(classifyState('ready')).toBe('ready')
    expect(classifyState('fault')).toBe('fault')
    expect(classifyState('Seq_loweringToCube')).toBe('busy')
    expect(classifyState('')).toBe('unknown')
  })
})
