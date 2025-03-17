import {Injectable} from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class ImageService {
  private image: File | null = null;

  constructor() {}

  setImage(image: File) {
    this.image = image;
  }

  getImage(): File | null {
    return this.image;
  }
}
