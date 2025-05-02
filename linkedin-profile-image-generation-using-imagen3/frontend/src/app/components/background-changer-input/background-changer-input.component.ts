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
