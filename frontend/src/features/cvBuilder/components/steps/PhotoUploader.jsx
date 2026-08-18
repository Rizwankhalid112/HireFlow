import { useRef } from 'react';
import { toast } from 'sonner';

import { Button } from '@/components/ui';

import { useDeletePhoto, useUploadPhoto } from '../../api/cvQueries';

const MAX_BYTES = 2 * 1024 * 1024;
const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp'];

export function PhotoUploader({ photoUrl }) {
  const inputRef = useRef(null);
  const uploadMutation = useUploadPhoto();
  const deleteMutation = useDeletePhoto();

  const onPick = (event) => {
    const file = event.target.files?.[0];
    event.target.value = ''; // allow re-picking the same file
    if (!file) return;

    // Mirrors the serializer so the user gets an instant answer.
    if (!ACCEPTED.includes(file.type)) {
      toast.error('Use a JPEG, PNG or WebP image.');
      return;
    }
    if (file.size > MAX_BYTES) {
      toast.error('Photo must be 2 MB or smaller.');
      return;
    }

    uploadMutation.mutate(file);
  };

  return (
    <div className="flex items-center gap-4 rounded-xl border border-slate-200 p-4 dark:border-slate-800">
      <div className="h-20 w-20 shrink-0 overflow-hidden rounded-full border border-slate-200 bg-slate-100 dark:border-slate-700 dark:bg-slate-800">
        {photoUrl ? (
          <img src={photoUrl} alt="Your CV photo" className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-2xl text-slate-400">
            👤
          </div>
        )}
      </div>

      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-slate-900 dark:text-slate-100">Profile photo</p>
        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
          JPEG, PNG or WebP · up to 2 MB. Resized to 600×600 and stripped of location data.
        </p>

        <div className="mt-3 flex gap-2">
          <Button
            size="sm"
            variant="secondary"
            loading={uploadMutation.isPending}
            onClick={() => inputRef.current?.click()}
          >
            {photoUrl ? 'Replace' : 'Upload photo'}
          </Button>
          {photoUrl ? (
            <Button
              size="sm"
              variant="ghost"
              className="text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950"
              loading={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
            >
              Remove
            </Button>
          ) : null}
        </div>

        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED.join(',')}
          className="hidden"
          onChange={onPick}
        />
      </div>
    </div>
  );
}
