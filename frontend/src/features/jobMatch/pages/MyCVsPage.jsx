import { useState } from 'react';
import { Link } from 'react-router-dom';

import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  Icon,
  IconButton,
  Modal,
  SkeletonRows,
} from '@/components/ui';
import { useCvVersion, useCvVersions, useDeleteCvVersion } from '@/features/cvBuilder/api/cvQueries';
import { downloadVersion } from '@/features/cvBuilder/utils/downloadVersion';

/*
 * The storage room.
 *
 * What a user wants months and fifty applications later is not "my CVs" — it is
 * "the one I sent to Acme". So the company is the heading and everything else
 * hangs off it, and the job description is kept beside the document because the
 * reason to open this at all is to revise before an interview.
 */

const scoreTone = (score) => (score >= 75 ? 'text-ok' : score >= 50 ? 'text-warn' : 'text-bad');

const formatDate = (value) =>
  new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });

function daysLeft(expiresAt) {
  const days = Math.ceil((new Date(expiresAt) - Date.now()) / 86_400_000);
  return days > 0 ? days : 0;
}

function VersionDetail({ id, onClose }) {
  const { data, isLoading } = useCvVersion(id);

  return (
    <Modal open={Boolean(id)} onClose={onClose} title={data?.company || 'Tailored CV'} size="lg">
      {isLoading || !data ? (
        <SkeletonRows rows={4} />
      ) : (
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <span className={`text-2xl leading-none font-medium tabular-nums ${scoreTone(data.match_score)}`}>
              {data.match_score}%
            </span>
            <div className="flex flex-col">
              <span className="text-xs font-semibold">{data.job_title || 'Role not stated'}</span>
              <span className="text-[11px] text-subtle">Tailored {formatDate(data.created_at)}</span>
            </div>
            {data.has_file ? (
              <Button
                className="ml-auto"
                size="sm"
                icon="download"
                onClick={() => downloadVersion(data)}
              >
                Download
              </Button>
            ) : null}
          </div>

          {data.applied_rewrites?.length ? (
            <section className="flex flex-col gap-1.5">
              <h3 className="text-xs font-bold">What we changed</h3>
              <ul className="flex flex-col gap-1">
                {data.applied_rewrites.map((item) => (
                  <li
                    key={`${item.current_wording}-${item.keyword}`}
                    className="flex flex-wrap items-center gap-1.5 text-xs"
                  >
                    <Icon name="check" size={12} className="text-ok" strokeWidth={2.8} />
                    <span className="text-subtle line-through">{item.current_wording}</span>
                    <Icon name="chevronRight" size={11} className="text-subtle" />
                    <span className="font-semibold text-ok">{item.keyword}</span>
                    <span className="text-[11px] text-subtle">
                      · {item.occurrences} {item.occurrences === 1 ? 'place' : 'places'}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {data.skipped_rewrites?.length ? (
            <section className="flex flex-col gap-1.5">
              <h3 className="text-xs font-bold">Left for you to do</h3>
              <ul className="flex flex-col gap-1 text-[11px] text-subtle">
                {data.skipped_rewrites.map((item) => (
                  <li key={`${item.current_wording}-${item.keyword}`}>
                    <span className="font-medium">{item.keyword}</span> — {item.reason}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {data.jd_text ? (
            <section className="flex flex-col gap-1.5">
              <h3 className="text-xs font-bold">The job you tailored this for</h3>
              <pre className="max-h-64 overflow-y-auto rounded-control border border-line bg-surface-2 p-3 font-sans text-[12px] leading-5 whitespace-pre-wrap text-muted">
                {data.jd_text}
              </pre>
            </section>
          ) : null}
        </div>
      )}
    </Modal>
  );
}

export default function MyCVsPage() {
  const { data: versions, isLoading } = useCvVersions();
  const [openId, setOpenId] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);
  const remove = useDeleteCvVersion();

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">My tailored CVs</h1>
        <p className="mt-0.5 text-xs text-muted">
          Every CV you tailored, filed under the company you sent it to. Open one before the
          interview to see exactly what you claimed.
        </p>
      </div>

      {isLoading ? (
        <SkeletonRows rows={4} />
      ) : !versions?.length ? (
        <Card>
          <div className="flex flex-col items-center gap-2 py-12 text-center">
            <Icon name="cv" size={22} className="text-subtle" />
            <p className="text-xs text-muted">
              Nothing here yet. Match your CV against a job, then accept the changes.
            </p>
            <Link to="/job-match">
              <Button size="sm" iconAfter="chevronRight">
                Match a job
              </Button>
            </Link>
          </div>
        </Card>
      ) : (
        <ul className="grid gap-2 sm:grid-cols-2">
          {versions.map((version) => (
            <li key={version.id}>
              <Card className="group flex h-full flex-col gap-2.5">
                <div className="flex items-start gap-2">
                  <div className="flex min-w-0 flex-col">
                    <button
                      type="button"
                      onClick={() => setOpenId(version.id)}
                      className="text-left text-sm font-semibold tracking-tight hover:text-accent"
                    >
                      {version.company || 'Company not stated'}
                    </button>
                    <span className="truncate text-xs text-muted">
                      {version.job_title || 'Role not stated'}
                    </span>
                  </div>
                  <span
                    className={`ml-auto shrink-0 text-lg leading-none font-medium tabular-nums ${scoreTone(version.match_score)}`}
                  >
                    {version.match_score}%
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-subtle">
                  <span>{formatDate(version.created_at)}</span>
                  <span className="text-line-strong">·</span>
                  {version.change_count ? (
                    <Badge variant="success">
                      {version.change_count} {version.change_count === 1 ? 'change' : 'changes'}
                    </Badge>
                  ) : (
                    <Badge>change list only</Badge>
                  )}
                  {/* Retention is visible rather than a surprise: these are
                      deleted on a schedule, and finding out by absence is the
                      worst way to learn it. */}
                  <span className="ml-auto">Kept {daysLeft(version.expires_at)} more days</span>
                </div>

                <div className="mt-auto flex items-center gap-1.5">
                  <Button variant="secondary" size="sm" onClick={() => setOpenId(version.id)}>
                    Open
                  </Button>
                  {version.has_file ? (
                    <Button size="sm" icon="download" onClick={() => downloadVersion(version)}>
                      Download
                    </Button>
                  ) : null}
                  <IconButton
                    icon="trash"
                    label={`Remove the CV tailored for ${version.company || 'this role'}`}
                    size="sm"
                    onClick={() => setPendingDelete(version)}
                    className="ml-auto transition-opacity sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100"
                  />
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}

      <VersionDetail id={openId} onClose={() => setOpenId(null)} />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onClose={() => setPendingDelete(null)}
        loading={remove.isPending}
        title="Remove this tailored CV?"
        description={
          `The CV tailored for ${pendingDelete?.company || 'this role'} will be deleted. ` +
          'Your original CV is not affected.'
        }
        confirmLabel="Remove"
        onConfirm={() =>
          remove.mutate(pendingDelete.id, { onSuccess: () => setPendingDelete(null) })
        }
      />
    </div>
  );
}
