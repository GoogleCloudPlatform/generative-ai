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
