/**
 * Extract pure base64 data from data URL (e.g., "data:image/jpeg;base64,...")
 */
export function extractBase64FromDataUrl(dataUrl: string): string {
  return dataUrl.split(',')[1];
}
