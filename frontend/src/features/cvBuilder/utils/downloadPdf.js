/*
 * Save the previewed bytes to disk.
 *
 * Deliberately client-side: these are the exact bytes the preview endpoint
 * returned, so the downloaded file is the document the user was looking at —
 * not a second render that could differ.
 */

function fileName(fullName) {
  const base = (fullName || 'cv').trim().toLowerCase().replace(/[^a-z0-9]+/g, '-');
  return `${base.replace(/^-|-$/g, '') || 'cv'}-cv.pdf`;
}

export function downloadPdf(data, fullName) {
  if (!data) {
    return;
  }

  // slice(0) because pdf.js detaches the buffer it is handed, and the same
  // ArrayBuffer is shared with the canvas renderer.
  const blob = new Blob([data.slice(0)], { type: 'application/pdf' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = fileName(fullName);
  document.body.appendChild(link);
  link.click();
  link.remove();

  // Revoke late so the browser has claimed the blob first.
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
