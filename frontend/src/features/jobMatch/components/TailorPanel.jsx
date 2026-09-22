import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { Alert, Button, Checkbox, Icon, Panel, SkeletonText } from '@/components/ui';
import { useTailorCv, useTailorPreview } from '@/features/cvBuilder/api/cvQueries';
import { downloadVersion } from '@/features/cvBuilder/utils/downloadVersion';

/*
 * Turning the reworded list into a document.
 *
 * Only this bucket is ever offered. `missing` is a question — applying it would
 * mean writing a claim onto a CV the user has to defend in an interview — and
 * `matched` is already correct by definition.
 *
 * Everything is ticked by default because every one of these renames something
 * the CV already says, and each is untickable individually because the user is
 * the one who has to stand behind the document.
 */

const rowKey = (item) => `${item.current_wording}=>${item.keyword}`;

export function TailorPanel({ matchId, company }) {
  const { data, isLoading } = useTailorPreview(matchId);
  const tailor = useTailorCv(matchId);
  const [excluded, setExcluded] = useState(() => new Set());
  const [result, setResult] = useState(null);

  const planned = useMemo(() => data?.planned ?? [], [data]);
  const skipped = data?.skipped ?? [];
  const chosen = planned.filter((item) => !excluded.has(rowKey(item)));

  if (isLoading) {
    return (
      <Panel title="Tailor this CV">
        <SkeletonText lines={3} />
      </Panel>
    );
  }

  if (!planned.length && !skipped.length) return null;

  const toggle = (item) =>
    setExcluded((prev) => {
      const next = new Set(prev);
      const id = rowKey(item);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const onTailor = () =>
    tailor.mutate(
      chosen.length === planned.length
        ? undefined
        : chosen.map((item) => ({
            keyword: item.keyword,
            current_wording: item.current_wording,
          })),
      { onSuccess: setResult },
    );

  if (result) {
    return (
      <Panel
        title="Tailored"
        description={`Saved for ${company || 'this role'}. Your original CV is untouched.`}
      >
        <div className="flex flex-col gap-3">
          {result.change_count ? (
            <ul className="flex flex-col gap-1.5">
              {result.applied_rewrites.map((item) => (
                <li key={rowKey(item)} className="flex flex-wrap items-center gap-1.5 text-xs">
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
          ) : (
            <Alert variant="warning">
              No file was produced — use the change list to update your CV by hand.
            </Alert>
          )}

          <div className="flex flex-wrap items-center gap-2">
            {result.has_file ? (
              <Button icon="download" onClick={() => downloadVersion(result)}>
                Download
              </Button>
            ) : null}
            <Link to="/my-cvs">
              <Button variant="secondary" iconAfter="chevronRight">
                All my tailored CVs
              </Button>
            </Link>
          </div>
        </div>
      </Panel>
    );
  }

  return (
    <Panel
      title="Tailor this CV"
      description="We swap only these words. Your template, layout and everything else stay exactly as they are."
    >
      <div className="flex flex-col gap-3">
        {data?.notice ? <Alert variant="warning">{data.notice}</Alert> : null}

        {planned.length ? (
          <ul className="flex flex-col divide-y divide-line rounded-control border border-line">
            {planned.map((item) => (
              <li key={rowKey(item)} className="flex items-center gap-2.5 px-3 py-2">
                <Checkbox
                  checked={!excluded.has(rowKey(item))}
                  onChange={() => toggle(item)}
                  aria-label={`Replace ${item.current_wording} with ${item.keyword}`}
                />
                <span className="flex min-w-0 flex-wrap items-center gap-1.5 text-xs">
                  <span className="text-subtle line-through">{item.current_wording}</span>
                  <Icon name="chevronRight" size={11} className="text-warn" strokeWidth={2.4} />
                  <span className="font-semibold text-warn">{item.keyword}</span>
                </span>
                <span className="tabular ml-auto shrink-0 text-[11px] text-subtle">
                  {item.occurrences} {item.occurrences === 1 ? 'place' : 'places'}
                </span>
              </li>
            ))}
          </ul>
        ) : null}

        {/* Shown, never hidden: a silent skip is indistinguishable from a bug. */}
        {skipped.length ? (
          <ul className="flex flex-col gap-1 text-[11px] text-subtle">
            {skipped.map((item) => (
              <li key={rowKey(item)} className="flex items-start gap-1.5">
                <Icon name="info" size={11} className="mt-0.5 shrink-0" />
                <span>
                  <span className="font-medium">{item.keyword}</span> — {item.reason}
                </span>
              </li>
            ))}
          </ul>
        ) : null}

        {planned.length ? (
          <div className="flex flex-wrap items-center gap-2">
            <Button loading={tailor.isPending} disabled={!chosen.length} onClick={onTailor}>
              {chosen.length === planned.length
                ? `Accept all ${planned.length} and tailor`
                : `Accept ${chosen.length} and tailor`}
            </Button>
            <span className="text-[11px] text-subtle">Nothing changes until you press this.</span>
          </div>
        ) : null}
      </div>
    </Panel>
  );
}
