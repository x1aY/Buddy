import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAudioCapture } from '../../src/composables/use-audio-capture'

describe('useAudioCapture', () => {
  const mockSendChunk = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    // Mock MediaRecorder which isn't available in jsdom
    global.MediaRecorder = vi.fn(() => ({
      start: vi.fn(),
      stop: vi.fn(),
      ondataavailable: vi.fn(),
      state: 'inactive',
    })) as unknown as typeof MediaRecorder
  })

  it('should initialize with default enabled state', () => {
    const { isEnabled } = useAudioCapture(mockSendChunk)
    expect(isEnabled.value).toBe(false) // DEFAULT_AUDIO_ENABLED is false
  })

  it('should toggle enabled state', async () => {
    const { isEnabled, toggle } = useAudioCapture(mockSendChunk)
    const initialState = isEnabled.value

    await toggle()
    expect(isEnabled.value).toBe(!initialState)

    // When toggling off, it should work without calling getUserMedia
    await toggle()
    expect(isEnabled.value).toBe(initialState)
  })

  it('should allow manual setting of enabled state', () => {
    const { isEnabled, setEnabled } = useAudioCapture(mockSendChunk)

    setEnabled(false)
    expect(isEnabled.value).toBe(false)

    setEnabled(true)
    expect(isEnabled.value).toBe(true)
  })
})
