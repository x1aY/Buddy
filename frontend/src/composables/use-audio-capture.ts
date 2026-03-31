import { ref, onUnmounted } from 'vue';
import { DEFAULT_AUDIO_ENABLED } from '@seeworldweb/shared/src/constants';

const BUFFER_SIZE = 2048;
const TARGET_SAMPLE_RATE = 16000;

export function useAudioCapture(sendChunk: (base64Audio: string) => void) {
  const isEnabled = ref<boolean>(DEFAULT_AUDIO_ENABLED);
  const stream = ref<MediaStream | null>(null);
  const audioContext = ref<AudioContext | null>(null);
  const scriptProcessor = ref<ScriptProcessorNode | null>(null);
  const audioInput = ref<MediaStreamAudioSourceNode | null>(null);
  let audioChunkCounter = 0;
  const LOG_INTERVAL = 10; // Log every 10 chunks

  // Processing queue to ensure correct order after async resampling
  let processingQueue: Promise<void> = Promise.resolve();

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

  // Resample audio buffer to target sample rate using OfflineAudioContext
  async function resampleBuffer(
    inputBuffer: AudioBuffer,
    fromSampleRate: number,
    toSampleRate: number
  ): Promise<Float32Array> {
    const numberOfChannels = 1;
    const duration = inputBuffer.length / fromSampleRate;
    const offlineContext = new OfflineAudioContext(
      numberOfChannels,
      Math.ceil(duration * toSampleRate),
      toSampleRate
    );
    const source = offlineContext.createBufferSource();
    source.buffer = inputBuffer;
    source.connect(offlineContext.destination);
    source.start();
    const resampledBuffer = await offlineContext.startRendering();
    return resampledBuffer.getChannelData(0);
  }

  async function start(): Promise<void> {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        },
        video: false
      });

      stream.value = mediaStream;

      // Don't force sample rate - let browser use default, then we'll resample
      const context = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioContext.value = context;
      const actualSampleRate = context.sampleRate;

      console.log(`[Audio] AudioContext created. Actual sample rate: ${actualSampleRate}Hz, will resample to ${TARGET_SAMPLE_RATE}Hz`);

      const source = context.createMediaStreamSource(mediaStream);
      audioInput.value = source;

      const processor = context.createScriptProcessor(BUFFER_SIZE, 1, 1);
      scriptProcessor.value = processor;

      let firstChunkLogged = false;

      processor.onaudioprocess = (event) => {
        // Get mono channel data at original sample rate
        const inputData = event.inputBuffer.getChannelData(0);

        if (!firstChunkLogged) {
          console.log(`[Audio] First PCM chunk received, buffer size: ${inputData.length} samples @ ${actualSampleRate}Hz`);
          firstChunkLogged = true;
        }

        // Chain processing to preserve order - async resampling must not reorder chunks
        processingQueue = processingQueue.then(async () => {
          let pcmData: Int16Array;

          if (actualSampleRate === TARGET_SAMPLE_RATE) {
            // No resampling needed
            pcmData = new Int16Array(inputData.length);
            for (let i = 0; i < inputData.length; i++) {
              pcmData[i] = Math.max(-1, Math.min(1, inputData[i])) * 0x7FFF;
            }
          } else {
            // Need to resample
            const originalBuffer = context.createBuffer(1, inputData.length, actualSampleRate);
            originalBuffer.copyToChannel(inputData, 0);
            const resampled = await resampleBuffer(originalBuffer, actualSampleRate, TARGET_SAMPLE_RATE);
            pcmData = new Int16Array(resampled.length);
            for (let i = 0; i < resampled.length; i++) {
              pcmData[i] = Math.max(-1, Math.min(1, resampled[i])) * 0x7FFF;
            }
          }

          // Convert to little-endian bytes explicitly (required by Alibaba ASR)
          // Alibaba NLS requires 16-bit little-endian PCM
          const bytes = new Uint8Array(pcmData.length * 2);
          for (let i = 0; i < pcmData.length; i++) {
            const sample = pcmData[i];
            // Little-endian: lower 8 bits first
            bytes[i * 2] = sample & 0xFF;
            bytes[i * 2 + 1] = (sample >> 8) & 0xFF;
          }

          // Convert to base64 and send
          const blob = new Blob([bytes], { type: 'application/octet-stream' });
          const reader = new FileReader();
          reader.onloadend = () => {
            if (reader.result) {
              const base64 = (reader.result as string).split(',')[1];
              sendChunk(base64);
              audioChunkCounter++;
              if (import.meta.env.DEV && audioChunkCounter % LOG_INTERVAL === 0) {
                console.log(`[Audio] Sent ${audioChunkCounter} PCM chunks, last chunk size: ${base64.length} bytes (${pcmData.buffer.byteLength} bytes raw)`);
              }
            }
          };
          reader.readAsDataURL(blob);
        }).catch(err => {
          console.error('[Audio] Processing error', err);
        });
      };

      source.connect(processor);
      processor.connect(context.destination);

      console.log('Audio capture started (raw PCM 16kHz 16-bit mono after resampling)');
    } catch (error) {
      console.error('Failed to start audio capture:', error);
      throw error;
    }
  }

  function stop(): void {
    if (scriptProcessor.value) {
      scriptProcessor.value.disconnect();
    }
    if (audioInput.value) {
      audioInput.value.disconnect();
    }
    if (audioContext.value) {
      audioContext.value.close();
    }
    if (stream.value) {
      stream.value.getTracks().forEach(track => track.stop());
    }
    scriptProcessor.value = null;
    audioInput.value = null;
    audioContext.value = null;
    stream.value = null;
    processingQueue = Promise.resolve();
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
