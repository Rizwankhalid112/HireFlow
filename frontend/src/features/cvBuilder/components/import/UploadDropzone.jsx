import { useRef, useState } from 'react';

import { Alert, Button, Spinner } from '@/components/ui';

/*
 * Where an import starts: pick a PDF or DOCX, watch it get read.
 *
 * The client-side checks here duplicate the server's on purpose. They are not
 * the security boundary — the server sniffs magic bytes and is the real gate —
 * but telling someone their file is 12 MB before uploading 12 MB is the
 * difference between an instant answer and a slow one.
 */

const ACCEPT = '.pdf,.docx';
const MAX_BYTES = 5 * 1024 * 1024;

/* Reads as progress rather than as a list of states: the user does not care
   which of our two backend stages they are in, only that something is happening
   and roughly how far along. */
const STAGE_LABEL = {
  pending: 'Queued…',
  extracting: 'Reading your file…',
  parsing: 'Understanding your CV…',
};

function looksAcceptable(file) {
  const name = (file.name || '').toLowerCase();
  if (!name.endsWith('.pdf') && !name.endsWith('.docx')) {
    return name.endsWith('.doc')
      ? 'Old .doc files are not supported. Save as .docx or PDF and try again.'
      : 'Choose a PDF or DOCX file.';
  }
  if (file.size === 0) {
    return 'That file is empty.';
  }
  if (file.size > MAX_BYTES) {
    return 'File must be 5 MB or smaller.';
  }
  return null;
}

export function UploadDropzone({ onFile, status, progress, error, isUploading, onRetry }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [localError, setLocalError] = useState(null);

  const busy = isUploading || Boolean(STAGE_LABEL[status]);

  const handle = (file) => {
    if (!file) {
      return;
    }
    const problem = looksAcceptable(file);
    setLocalError(problem);
    if (!problem) {
      onFile(file);
    }
  };

  const onDrop = (event) => {
    event.preventDefault();
    setDragging(false);
    handle(event.dataTransfer.files?.[0]);
  };

  if (busy) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6 text-center dark:border-slate-700 dark:bg-slate-900">
        <Spinner />
        <p className="mt-3 text-sm font-medium text-slate-700 dark:text-slate-200">
          {isUploading ? 'Uploading…' : STAGE_LABEL[status]}
        </p>
        {isUploading && progress > 0 ? (
          <div className="mx-auto mt-3 h-1.5 w-48 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
            <div
              className="h-full rounded-full bg-slate-900 transition-[width] dark:bg-slate-100"
              style={{ width: `${progress}%` }}
            />
          </div>
        ) : null}
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
          This usually takes a few seconds. Nothing is changed on your CV until you review it.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`rounded-xl border-2 border-dashed p-6 text-center transition-colors ${
          dragging
            ? 'border-slate-900 bg-slate-50 dark:border-slate-100 dark:bg-slate-800'
            : 'border-slate-300 bg-white dark:border-slate-700 dark:bg-slate-900'
        }`}
      >
        <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
          Import from an existing CV
        </p>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
          Drop a PDF or DOCX here, or choose a file. Max 5 MB.
        </p>

        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="hidden"
          onChange={(event) => {
            handle(event.target.files?.[0]);
            // Reset so picking the same file twice still fires a change.
            event.target.value = '';
          }}
        />

        <Button className="mt-4" size="sm" onClick={() => inputRef.current?.click()}>
          Choose a file
        </Button>

        <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
          We read it and show you what we found. You choose what to keep.
        </p>
      </div>

      {localError ? (
        <Alert variant="error" className="mt-3">
          {localError}
        </Alert>
      ) : null}

      {error ? (
        <Alert variant="error" className="mt-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span>{error}</span>
            {onRetry ? (
              <Button size="sm" variant="ghost" onClick={onRetry}>
                Try again
              </Button>
            ) : null}
          </div>
        </Alert>
      ) : null}
    </div>
  );
}
