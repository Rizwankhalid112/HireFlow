import { toast } from 'sonner';

import { downloadCvVersion } from '../api/cvApi';

/*
 * Save a tailored CV to disk.
 *
 * Fetched rather than linked: the endpoint is authenticated and an anchor
 * cannot carry the Bearer token, so the bytes come back through axios and are
 * handed to a temporary object URL.
 */
export async function downloadVersion(version) {
  try {
    const { data } = await downloadCvVersion(version.id);
    const url = URL.createObjectURL(data);
    const link = document.createElement('a');
    link.href = url;
    link.download = version.file_name || 'tailored-cv';
    document.body.appendChild(link);
    link.click();
    link.remove();
    // Revoked on the next tick: revoking synchronously can beat the download in
    // some browsers and produce an empty file.
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch {
    toast.error('Could not download that file.');
  }
}
