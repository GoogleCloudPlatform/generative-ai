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
