/**
 * Copyright 2025 Google LLC
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

import {Injectable} from '@angular/core';
import {BehaviorSubject, Observable} from 'rxjs';

interface StoredImage {
  file: File | null;
  imageUrl: string | null;
  isUserPhotoUrl: boolean;
}

@Injectable({
  providedIn: 'root',
})
export class ImageService {
  private _selectedImage: BehaviorSubject<StoredImage | null> =
    new BehaviorSubject<StoredImage | null>(null);
  public selectedImage$: Observable<StoredImage | null> =
    this._selectedImage.asObservable();

  constructor() {
    // Initialize with null values
    this.setSelectedImage(null, null, false);
  }

  setSelectedImage(
    file: File | null,
    imageUrl: string | null,
    isUserPhotoUrl: boolean
  ) {
    this._selectedImage.next({file, imageUrl, isUserPhotoUrl});
  }

  getSelectedImage(): StoredImage | null {
    return this._selectedImage.getValue();
  }

  clearSelectedImage() {
    this._selectedImage.next(null);
  }
}
