import { useState } from "react";

import { api, errorMessage } from "../api";
import type { Experiment } from "../types";

const MAX_PHOTO_MB = 8;

/** Optional: Gemma looks at a photo of the plane. Shown as an estimate, never used by the model. */
export function PhotoCheck({ experiment, onChecked }: { experiment: Experiment; onChecked: (e: Experiment) => void }) {
  const [isChecking, setIsChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const check = experiment.photo_check;

  async function upload(file: File | undefined) {
    if (!file) return;
    if (file.size > MAX_PHOTO_MB * 1024 * 1024) {
      setError(`That photo is over ${MAX_PHOTO_MB} MB.`);
      return;
    }
    setIsChecking(true);
    setError(null);
    try {
      onChecked(await api.checkPhoto(experiment.id, file));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setIsChecking(false);
    }
  }

  return (
    <div className="space-y-2 px-4 py-4 text-sm">
      <p className="text-muted">
        Gemma can look at a photo and point out uneven wings before you throw. The photo isn't saved.
      </p>
      <label className="inline-flex min-h-10 cursor-pointer items-center rounded-md border border-line bg-white px-4 font-medium hover:bg-gray-50">
        {isChecking ? "Looking at it…" : check ? "Check another photo" : "Check a photo"}
        <input
          type="file"
          accept="image/*"
          capture="environment"
          className="sr-only"
          disabled={isChecking}
          onChange={(e) => upload(e.target.files?.[0])}
        />
      </label>
      {error && (
        <p role="alert" className="text-red-700">
          {error}
        </p>
      )}
      {check && (
        <div className="rounded-md border border-line p-3">
          <p className="text-xs text-muted">Estimate from a photo, {Math.round(check.confidence * 100)}% sure</p>
          <p className="mt-1">
            Wings look <strong>{check.symmetry}</strong>, nose looks <strong>{check.nose}</strong>
            {check.winglets_visible ? ", winglets visible" : ""}.
          </p>
          {check.comment && <p className="mt-1 text-muted">{check.comment}</p>}
        </div>
      )}
    </div>
  );
}
