import { useState } from "react";

import { api, errorMessage } from "../api";
import type { Experiment } from "../types";

const MAX_PHOTO_MB = 8;
// Plenty for Gemma to judge symmetry, and keeps a phone camera photo well under the upload limit.
const PHOTO_MAX_SIDE_PX = 1024;
const PHOTO_QUALITY = 0.85;

/** Shrinks a photo in the browser before upload. Returns the original if the browser can't decode it. */
async function shrinkPhoto(file: File): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, PHOTO_MAX_SIDE_PX / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d")?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", PHOTO_QUALITY));
    return blob ?? file;
  } catch {
    return file;
  }
}

/** Optional: Gemma looks at a photo of the plane. Shown as an estimate, never used by the model. */
export function PhotoCheck({ experiment, onChecked }: { experiment: Experiment; onChecked: (e: Experiment) => void }) {
  const [isChecking, setIsChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const check = experiment.photo_check;

  async function upload(file: File | undefined) {
    if (!file) return;
    setIsChecking(true);
    setError(null);
    try {
      const photo = await shrinkPhoto(file);
      if (photo.size > MAX_PHOTO_MB * 1024 * 1024) {
        setError(`That photo is over ${MAX_PHOTO_MB} MB.`);
        return;
      }
      onChecked(await api.checkPhoto(experiment.id, photo));
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
