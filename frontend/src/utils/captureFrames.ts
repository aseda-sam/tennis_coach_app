/**
 * Capture video frames at specific timestamps using a hidden <video> + canvas.
 * Extracted from ServeThumbnailStrip for reuse.
 */

export interface CapturedFrame {
  timestamp: number;
  label: string;
  dataUrl: string | null;
}

/**
 * Capture a single frame from a video at a given timestamp.
 */
function captureFrame(
  videoUrl: string,
  timestamp: number,
  quality = 0.85
): Promise<string | null> {
  return new Promise((resolve) => {
    const video = document.createElement('video');
    video.crossOrigin = 'anonymous';
    video.preload = 'metadata';
    video.muted = true;

    const cleanup = () => {
      video.removeAttribute('src');
      video.load();
    };

    video.addEventListener(
      'seeked',
      () => {
        try {
          const canvas = document.createElement('canvas');
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          const ctx = canvas.getContext('2d');
          if (ctx) {
            ctx.drawImage(video, 0, 0);
            resolve(canvas.toDataURL('image/jpeg', quality));
          } else {
            resolve(null);
          }
        } catch {
          resolve(null);
        } finally {
          cleanup();
        }
      },
      { once: true }
    );

    video.addEventListener(
      'error',
      () => {
        cleanup();
        resolve(null);
      },
      { once: true }
    );

    video.src = videoUrl;
    video.addEventListener(
      'loadedmetadata',
      () => {
        video.currentTime = Math.min(timestamp, video.duration);
      },
      { once: true }
    );
  });
}

/**
 * Capture frames at multiple timestamps sequentially.
 * Returns array in the same order as `targets`.
 */
export async function captureFramesAtTimestamps(
  videoUrl: string,
  targets: { timestamp: number; label: string }[],
  options?: {
    quality?: number;
    onProgress?: (done: number, total: number) => void;
  }
): Promise<CapturedFrame[]> {
  const quality = options?.quality ?? 0.85;
  const results: CapturedFrame[] = [];

  for (let i = 0; i < targets.length; i++) {
    const { timestamp, label } = targets[i];
    const dataUrl = await captureFrame(videoUrl, timestamp, quality);
    results.push({ timestamp, label, dataUrl });
    options?.onProgress?.(i + 1, targets.length);
  }

  return results;
}
