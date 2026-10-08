/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

export interface AvatarTarget {
  width: number;
  height: number;
}

// Portrait and landscape reference-image dimensions for Live Avatar's
// CustomizedAvatar, as measured against the Live API:
// Live models accept either orientation, and landscape input gets
// normalized by the API to a canonical 1280x704 output regardless of the
// exact input aspect ratio.
export const AVATAR_PORTRAIT: AvatarTarget = { width: 704, height: 1280 };
export const AVATAR_LANDSCAPE: AvatarTarget = { width: 1280, height: 704 };

// Picks the Live Avatar reference-image target that crops the LEAST out of
// a given source image. A source wider than it is tall crops least as
// landscape; taller than wide (or square) crops least as portrait.
export function pickAvatarTarget(
  sourceWidth: number,
  sourceHeight: number,
): AvatarTarget {
  return sourceWidth > sourceHeight ? AVATAR_LANDSCAPE : AVATAR_PORTRAIT;
}

export async function resizeAndCropImage(
  dataUrl: string,
  targetWidth?: number,
  targetHeight?: number,
): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const target =
        targetWidth && targetHeight
          ? { width: targetWidth, height: targetHeight }
          : pickAvatarTarget(img.width, img.height);

      const canvas = document.createElement('canvas');
      canvas.width = target.width;
      canvas.height = target.height;
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        return reject(new Error('Failed to get canvas context'));
      }

      // Calculate crop dimensions to maintain aspect ratio and fill the target
      const imgRatio = img.width / img.height;
      const targetRatio = target.width / target.height;

      let drawWidth = img.width;
      let drawHeight = img.height;
      let offsetX = 0;
      let offsetY = 0;

      if (imgRatio > targetRatio) {
        // Image is wider than target ratio
        drawWidth = img.height * targetRatio;
        offsetX = (img.width - drawWidth) / 2;
      } else {
        // Image is taller than target ratio
        drawHeight = img.width / targetRatio;
        offsetY = (img.height - drawHeight) / 2;
      }

      ctx.drawImage(
        img,
        offsetX,
        offsetY,
        drawWidth,
        drawHeight, // Source crop
        0,
        0,
        target.width,
        target.height, // Destination size
      );

      // Output as JPEG to ensure compatibility and manage size
      resolve(canvas.toDataURL('image/jpeg', 0.9));
    };
    img.onerror = () => reject(new Error('Failed to load image'));
    img.src = dataUrl;
  });
}

export async function resizeToMaxDimension(
  dataUrl: string,
  maxDim = 1024,
): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      let width = img.width;
      let height = img.height;
      if (width <= maxDim && height <= maxDim) {
        return resolve(dataUrl);
      }
      if (width > height) {
        height = Math.round((height * maxDim) / width);
        width = maxDim;
      } else {
        width = Math.round((width * maxDim) / height);
        height = maxDim;
      }
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      if (!ctx) return reject(new Error('Failed to get canvas context'));
      ctx.drawImage(img, 0, 0, width, height);
      resolve(canvas.toDataURL('image/jpeg', 0.85));
    };
    img.onerror = () => reject(new Error('Failed to load image for resize'));
    img.src = dataUrl;
  });
}
