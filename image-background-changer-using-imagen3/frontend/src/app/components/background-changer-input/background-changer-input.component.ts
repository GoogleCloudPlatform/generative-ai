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
  ViewChild,
  ElementRef,
  Output,
  EventEmitter,
} from '@angular/core';

@Component({
  selector: 'app-background-changer-input',
  templateUrl: './background-changer-input.component.html',
  styleUrls: ['./background-changer-input.component.scss'],
})
export class BackgroundChangerInputComponent {
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;
  imageUrl: string | ArrayBuffer | null = null;
  selectedFile: File | null = null;

  @Output() emitSearch: EventEmitter<File> = new EventEmitter();

  constructor() {}

  onFileSelected(event: any): void {
    const file: File = event.target.files[0];

    if (file) {
      this.selectedFile = file;
      const reader = new FileReader();
      reader.onload = (e: any) => {
        this.imageUrl = e.target.result;
      };
      reader.readAsDataURL(file);
    } else {
      this.imageUrl = null;
      this.selectedFile = null;
    }
  }

  onSubmit(): void {
    if (this.selectedFile) {
      this.emitSearch.emit(this.selectedFile); // Emit the file
    } else {
      console.log('No image selected to submit.');
    }
  }
}
