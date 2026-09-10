import { useEffect, useState } from 'react';

import {
  useApplyImport,
  useRetryUploadParse,
  useUploadCv,
  useUploadStatus,
} from '../../api/cvQueries';
import { ImportReviewModal } from './ImportReviewModal';
import { UploadDropzone } from './UploadDropzone';

/*
 * Owns one import from file to applied.
 *
 * The state machine is deliberately in one component rather than spread across
 * the dropzone and the modal: upload → poll → review → apply has four failure
 * points, and tracking which one you are in from two places is how a stuck
 * spinner ships.
 *
 * The rule the whole flow exists to enforce: the CV does not change until the
 * user has seen what we found and said yes. An empty CV skips the modal, since
 * reviewing a diff against nothing is a dialog for no reason — but that is a
 * shortcut through the review, not around the apply.
 */

/* A terminal status that produced no usable data. Each one has a message from
   the backend that says what to do, so the panel renders that rather than
   inventing its own copy. */
const FAILED_STATUSES = ['failed', 'scanned'];

export function ImportPanel({ onImported }) {
  const [logId, setLogId] = useState(null);
  const [progress, setProgress] = useState(0);
  const [reviewing, setReviewing] = useState(false);
  const [capMessage, setCapMessage] = useState(null);

  const upload = useUploadCv();
  const retry = useRetryUploadParse();
  const apply = useApplyImport();
  const { data: status } = useUploadStatus(logId);

  const parseFinished = status?.is_terminal && !FAILED_STATUSES.includes(status.status);

  const applyChoices = (choices, answers) => {
    apply.mutate(
      { logId, choices, answers },
      {
        onSuccess: () => {
          setReviewing(false);
          setLogId(null);
          setProgress(0);
          onImported?.();
        },
      },
    );
  };

  useEffect(() => {
    if (!parseFinished) {
      return;
    }
    // A CV with nothing on it has nothing to overwrite, so there is nothing to
    // review — but it still goes through apply, which is the only writer.
    if (status.requires_review) {
      setReviewing(true);
    } else {
      applyChoices(everySectionFrom(status.parsed_data), {});
    }
    // Keyed on the transition into a finished parse, not on applyChoices, which
    // is a new closure every render — depending on it would re-apply an import
    // that is already done.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parseFinished, status?.requires_review]);

  const onFile = (file) => {
    setCapMessage(null);
    setProgress(0);
    upload.mutate(
      { file, onProgress: setProgress },
      {
        onSuccess: (data) => setLogId(data.log_id),
        onError: (error) => {
          if (error?.response?.status === 429) {
            setCapMessage(error.response.data?.detail);
          }
        },
      },
    );
  };

  const failureMessage = capMessage
    || (status && FAILED_STATUSES.includes(status.status) ? status.error_message : null);

  return (
    <>
      <UploadDropzone
        onFile={onFile}
        status={logId ? status?.status : null}
        progress={progress}
        error={failureMessage}
        isUploading={upload.isPending}
        // Retry re-runs the AI stage on text we already have. It is only
        // offered when there is text to re-parse — a scanned file has none, and
        // retrying it would fail identically.
        onRetry={
          status?.status === 'failed' && !capMessage
            ? () => retry.mutate(logId)
            : undefined
        }
      />

      {reviewing ? (
        <ImportReviewModal
          open
          onClose={() => {
            setReviewing(false);
            setLogId(null);
          }}
          parsed={status?.parsed_data}
          existing={status?.existing_data}
          onApply={applyChoices}
          isApplying={apply.isPending}
        />
      ) : null}
    </>
  );
}

/* For an empty CV: take everything that came back. `replace` and `merge` are
   equivalent against nothing, and `replace` is the one that also fills the
   profile's own fields. */
function everySectionFrom(parsed) {
  const sections = [
    'personal', 'work_experience', 'education', 'skills',
    'projects', 'certifications', 'languages',
  ];
  return Object.fromEntries(
    sections
      .filter((key) => (key === 'personal'
        ? Object.values(parsed?.personal ?? {}).some(Boolean)
        : (parsed?.[key] ?? []).length > 0))
      .map((key) => [key, 'replace']),
  );
}
