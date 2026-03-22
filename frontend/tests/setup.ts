import { vi } from 'vitest'
import { config } from '@vue/test-utils'

// Global test setup
// Mock intersection observer
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: () => {},
  unobserve: () => {},
  disconnect: () => {},
}))

// Mock media devices for camera/audio tests
if (!global.navigator?.mediaDevices) {
  Object.defineProperty(global.navigator, 'mediaDevices', {
    value: {
      getUserMedia: vi.fn().mockResolvedValue({
        getTracks: () => [{ stop: vi.fn() }],
      }),
    },
    writable: true,
  })
}
