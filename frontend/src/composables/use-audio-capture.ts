import { ref, onUnmounted } from 'vue';
import { DEFAULT_AUDIO_ENABLED } from '@seeworldweb/shared/src/constants';
import { AUDIO_CHUNK_INTERVAL_MS, AUDIO_MIME_TYPE } from '@seeworldweb/shared/src/constants';

export function useAudioCapture(sendChunk: (base64Audio: string) => void) {
  const isEnabled = ref<boolean>(DEFAULT_AUDIO_ENABLED);
  const mediaRecorder = ref<MediaRecorder | null>(null);
  const stream = ref<MediaStream | null>(null);

  async function toggle(): Promise<boolean> {
    const newState = !isEnabled.value;
    if (newState) {
      await start();
    } else {
      stop();
    }
    isEnabled.value = newState;
    return isEnabled.value;
  }

  async function start(): Promise<void> {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000
        },
        video: false
      });

      stream.value = mediaStream;
      const recorder = new MediaRecorder(mediaStream, {
        mimeType: AUDIO_MIME_TYPE
      });

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          // Convert blob to base64 and send
          const reader = new FileReader();
          reader.onloadend = () => {
            const base64 = (reader.result as string).split(',')[1];
            sendChunk(base64);
          };
          reader.readAsDataURL(event.data);
        }
      };

      // Start recording and collect chunks periodically
      recorder.start(AUDIO_CHUNK_INTERVAL_MS);
      mediaRecorder.value = recorder;

      console.log('Audio capture started');
    } catch (error) {
      console.error('Failed to start audio capture:', error);
      throw error;
    }
  }

  function stop(): void {
    if (mediaRecorder.value && mediaRecorder.value.state !== 'inactive') {
      mediaRecorder.value.stop();
    }
    if (stream.value) {
      stream.value.getTracks().forEach(track => track.stop());
    }
    mediaRecorder.value = null;
    stream.value = null;
    console.log('Audio capture stopped');
  }

  function setEnabled(enabled: boolean): void {
    isEnabled.value = enabled;
  }

  onUnmounted(() => {
    stop();
  });

  return {
    isEnabled,
    toggle,
    start,
    stop,
    setEnabled
  };
}
