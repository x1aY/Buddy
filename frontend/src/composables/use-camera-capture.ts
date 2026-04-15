import { ref, onUnmounted } from 'vue';
import { DEFAULT_CAMERA_ENABLED } from '@buddy/shared/src/constants';
import {
  CAMERA_FRAME_INTERVAL_MS,
  CAMERA_FRAME_QUALITY,
  CAMERA_FRAME_MAX_WIDTH
} from '@buddy/shared/src/constants';
import { extractBase64FromDataUrl } from '@/utils/image';

export function useCameraCapture(sendFrame: (base64Image: string) => void) {
  const isEnabled = ref<boolean>(DEFAULT_CAMERA_ENABLED);
  const stream = ref<MediaStream | null>(null);
  const videoElement = ref<HTMLVideoElement | null>(null);
  const canvasElement = ref<HTMLCanvasElement | null>(null);
  const canvasContext = ref<CanvasRenderingContext2D | null>(null);
  const intervalId = ref<number | null>(null);
  let lastSentFrame: string | null = null;

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
        video: {
          width: { max: CAMERA_FRAME_MAX_WIDTH },
          facingMode: 'user'
        },
        audio: false
      });

      stream.value = mediaStream;

      // Create video element for streaming
      const video = document.createElement('video');
      video.srcObject = mediaStream;
      video.autoplay = true;
      video.muted = true;
      videoElement.value = video;

      // Create canvas for capturing frames
      const canvas = document.createElement('canvas');
      canvasElement.value = canvas;

      await video.play();

      // Cache context once after canvas creation
      canvasContext.value = canvas.getContext('2d');

      // Set canvas size once after video is playing
      if (video.videoWidth && canvasContext.value) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
      }

      // Start capturing frames at interval (1fps reduces bandwidth usage)
      intervalId.value = window.setInterval(() => {
        captureFrame();
      }, CAMERA_FRAME_INTERVAL_MS);

      console.log('Camera capture started');
    } catch (error) {
      console.error('Failed to start camera:', error);
      throw error;
    }
  }

  function captureFrame(): void {
    if (!videoElement.value || !canvasElement.value || !canvasContext.value || !stream.value) return;

    const video = videoElement.value;
    const canvas = canvasElement.value;
    const ctx = canvasContext.value;

    // Only update size if video dimensions changed (rare)
    if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
    }

    // Draw current frame
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert to base64 JPEG
    const base64 = canvas.toDataURL('image/jpeg', CAMERA_FRAME_QUALITY);
    const pureBase64 = extractBase64FromDataUrl(base64);

    // Only send changed frames
    if (base64 !== lastSentFrame) {
      sendFrame(pureBase64);
      lastSentFrame = base64;
      if (import.meta.env.DEV) {
        console.log(`[Camera] Sent frame, size: ${pureBase64.length} bytes`);
      }
    }
  }

  function stop(): void {
    if (intervalId.value) {
      clearInterval(intervalId.value);
      intervalId.value = null;
    }
    if (stream.value) {
      stream.value.getTracks().forEach(track => track.stop());
    }
    videoElement.value = null;
    canvasElement.value = null;
    stream.value = null;
    console.log('Camera capture stopped');
  }

  function getVideoStream(): MediaStream | null {
    return stream.value;
  }

  onUnmounted(() => {
    stop();
  });

  return {
    isEnabled,
    toggle,
    start,
    stop,
    getVideoStream
  };
}
