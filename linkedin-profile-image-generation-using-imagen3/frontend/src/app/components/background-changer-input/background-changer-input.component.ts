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

import {
  Component,
  EventEmitter,
  Output,
  OnInit,
  OnDestroy,
} from '@angular/core';
import {DomSanitizer} from '@angular/platform-browser';
import {ImageService} from 'src/app/services/image/image.service';

@Component({
  selector: 'app-background-changer-input',
  templateUrl: './background-changer-input.component.html',
  styleUrls: ['./background-changer-input.component.scss'],
})
export class BackgroundChangerInputComponent implements OnInit, OnDestroy {
  @Output() emitSearch = new EventEmitter<any>();
  selectedFile: File | null = null;
  imageUrl: any;
  userPhotoUrl: string | null = null;
  isUserPhotoUrl = false;

  constructor(
    private sanitizer: DomSanitizer,
    private _ImageService: ImageService
  ) {}

  ngOnInit(): void {}

  ngOnDestroy(): void {}

  onFileSelected(event: any) {
    if (event) {
      this.selectedFile = event.target.files[0];
      if (this.selectedFile) {
        const reader = new FileReader();
        reader.onload = (e: any) => {
          this.imageUrl = this.sanitizer.bypassSecurityTrustUrl(
            e.target.result
          );
          this._ImageService.setSelectedImage(
            this.selectedFile,
            e.target.result,
            false
          );
        };
        reader.readAsDataURL(this.selectedFile);
        this.isUserPhotoUrl = false;
      }
    }
  }

  loadImageFromUserUrl(url: string) {
    fetch(url)
      .then(response => response.blob())
      .then(blob => {
        this.selectedFile = new File([blob], 'user_photo.jpg', {
          type: blob.type,
        });
        const reader = new FileReader();
        reader.onload = (e: any) => {
          this.imageUrl = this.sanitizer.bypassSecurityTrustUrl(
            e.target.result
          );
          this._ImageService.setSelectedImage(
            this.selectedFile,
            e.target.result,
            true
          );
        };
        reader.readAsDataURL(this.selectedFile);
      });
  }

  onSubmit(): void {
    if (this.selectedFile) {
      this.emitSearch.emit({
        file: this.selectedFile,
        isUserPhotoUrl: this.isUserPhotoUrl,
      });
    } else {
      console.log('No image selected to submit.');
    }
  }
}
