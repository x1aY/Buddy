import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import AudioToggle from '../../src/components/AudioToggle.vue'

describe('AudioToggle', () => {
  it('should display 🔊 and "声音开启" when enabled is true', () => {
    const wrapper = mount(AudioToggle, {
      props: {
        enabled: true,
      },
    })

    expect(wrapper.find('.audio-toggle').classes()).toContain('enabled')
    expect(wrapper.text()).toContain('声音开启')
    expect(wrapper.text()).toContain('🔊')
  })

  it('should display 🔇 and "声音关闭" when enabled is false', () => {
    const wrapper = mount(AudioToggle, {
      props: {
        enabled: false,
      },
    })

    expect(wrapper.find('.audio-toggle').classes()).not.toContain('enabled')
    expect(wrapper.text()).toContain('声音关闭')
    expect(wrapper.text()).toContain('🔇')
  })

  it('should emit toggle event when clicked', async () => {
    const wrapper = mount(AudioToggle, {
      props: {
        enabled: true,
      },
    })

    await wrapper.trigger('click')
    expect(wrapper.emitted().toggle).toBeTruthy()
    expect(wrapper.emitted().toggle.length).toBe(1)
  })
})
