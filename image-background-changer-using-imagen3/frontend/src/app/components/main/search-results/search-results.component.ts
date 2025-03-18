import {Component, OnDestroy, ViewChild, TemplateRef} from '@angular/core';
import {SearchService} from 'src/app/services/search.service';
import {ReplaySubject, takeUntil} from 'rxjs';
import {UserService} from 'src/app/services/user/user.service';
import {ActivatedRoute, Router} from '@angular/router';
import {
  search_document_type,
  search_image_type,
  PDF,
  image_name,
} from 'src/environments/constant';
import {
  DomSanitizer,
  SafeResourceUrl,
  SafeUrl,
} from '@angular/platform-browser';
import {MatDialog} from '@angular/material/dialog';
import {GeneratedImage} from 'src/app/models/generated-image.model';
import {SearchRequest} from 'src/app/models/search.model';
import {MatSnackBar} from '@angular/material/snack-bar';
import {ToastMessageComponent} from '../../toast-message/toast-message.component';
import {MatButtonToggleChange} from '@angular/material/button-toggle';

interface Imagen3Model {
  value: string;
  viewValue: string;
}

interface ImageStylesModel {
  value: string;
  viewValue: string;
}

@Component({
  selector: 'app-search-results',
  templateUrl: './search-results.component.html',
  styleUrls: ['./search-results.component.scss'],
})
export class SearchResultsComponent implements OnDestroy {
  @ViewChild('preview', {static: true})
  previewRef!: TemplateRef<{}>;
  summary = '';
  private readonly destroyed = new ReplaySubject<void>(1);
  serachResult: any = [];
  documents: any = [];
  showDefaultDocuments: boolean = false;
  images: any = [];
  pdf = PDF;
  imageName = image_name;
  documentURL: SafeResourceUrl | undefined;
  openPreviewDocument: any;
  currentPage = 0;
  pageSize = 4;
  selectedDocument: any;
  safeUrl: SafeUrl | undefined;
  selectedResult: GeneratedImage | undefined;
  imagen3ModelsList: Imagen3Model[] = [
    {
      value: 'imagen-3.0-capability-001',
      viewValue: 'Imagen 3: imagen-3.0-capability-001',
    },
    // {value: 'imagegeneration@006', viewValue: 'Imagen 2: imagegeneration@006'},
  ];
  selectedModel = this.imagen3ModelsList[0].value;
  imageStylesList: ImageStylesModel[] = [
    {value: 'Modern', viewValue: 'Modern'},
    {value: 'Realistic', viewValue: 'Realistic'},
    {value: 'Vintage', viewValue: 'Vintage'},
    {value: 'Monochrome', viewValue: 'Monochrome'},
    {value: 'Fantasy', viewValue: 'Fantasy'},
  ];
  selectedStyle: string = this.imageStylesList[0].value;
  selectedNumberOfResults: number = 4;
  selectedMaskDistilation: number = 0.005;
  searchRequest: SearchRequest = {
    term: '',
    model: this.selectedModel,
    imageStyle: this.selectedStyle,
    numberOfResults: this.selectedNumberOfResults,
    maskDistilation: this.selectedMaskDistilation,
  };

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private service: SearchService,
    private userService: UserService,
    private dialog: MatDialog,
    private sanitizer: DomSanitizer,
    private _snackBar: MatSnackBar
  ) {
    const query = this.route.snapshot.queryParamMap.get('q');
    this.userService.showLoading();

    if (!query) {
      this.documents = [
        {
          enhancedPrompt: 'default enhaced prompt',
          raiFilteredReason: null,
          image: {
            gcsUri: null,
            mimeType: 'image/png',
            encodedImage: 'assets/images/placeholder_image.png',
          },
        },
      ];
      this.showDefaultDocuments = true;
      this.userService.hideLoading();
      return;
    }

    this.searchRequest.term = query || '';
    const newSearchRequest = this.searchRequest;

    this.service.search(newSearchRequest).subscribe({
      next: (searchResponse: GeneratedImage[]) => {
        this.summary = searchResponse?.[0]?.enhancedPrompt || '';
        this.documents = searchResponse;
        this.serachResult.forEach((element: GeneratedImage) => {
          this.images.push(element.image?.encodedImage);
        });
        this.selectedResult = searchResponse[0];

        this.userService.hideLoading();
      },
      error: error => {
        console.error('Search error:', error);

        this.documents = [
          {
            enhancedPrompt: 'default enhaced prompt',
            raiFilteredReason: null,
            image: {
              gcsUri: null,
              mimeType: 'image/png',
              encodedImage: 'assets/images/placeholder_image.png',
            },
          },
        ];
        this.showDefaultDocuments = true;
        this.userService.hideLoading();

        this._snackBar.openFromComponent(ToastMessageComponent, {
          panelClass: ['red-toast'],
          verticalPosition: 'top',
          horizontalPosition: 'right',
          duration: 5000,
          data: {
            text:
              `${error?.error?.detail?.[0]?.msg} - ${error?.error?.detail?.[0]?.loc}` ||
              error?.error?.detail ||
              'Error sending request. Please try again later!',
            icon: 'cross-in-circle-white',
          },
        });
      },
    });
  }

  searchTerm({
    term,
    model,
    imageStyle,
    numberOfResults,
    maskDistilation,
  }: {
    term?: string | undefined;
    model?: string | undefined;
    imageStyle?: string | undefined;
    numberOfResults?: number | undefined;
    maskDistilation?: number | undefined;
  }) {
    if (!term) return;

    this.showDefaultDocuments = false;
    this.userService.showLoading();
    this.serachResult = [];
    this.summary = '';
    this.documents = [];
    this.images = [];
    // this.router.navigate(['/search'], {queryParams: {q: term}});

    if (term) this.searchRequest.term = term;
    if (model) this.searchRequest.model = model;
    if (imageStyle) this.searchRequest.imageStyle = imageStyle;
    if (numberOfResults) this.searchRequest.numberOfResults = numberOfResults;
    if (maskDistilation) this.searchRequest.maskDistilation = maskDistilation;

    const newSearchRequest = this.searchRequest;

    this.service.search(newSearchRequest).subscribe({
      next: (searchResponse: any) => {
        this.summary = searchResponse?.[0]?.enhancedPrompt || '';
        this.documents = searchResponse;
        this.serachResult.forEach((element: GeneratedImage) => {
          this.images.push(element.image?.encodedImage);
        });
        this.selectedResult = searchResponse[0];
        this.userService.hideLoading();
      },
      error: error => {
        console.error('Search error:', error);
        this.userService.hideLoading();
      },
    });
  }

  openNewWindow(link: string) {
    window.open(link, '_blank');
  }

  changeImageSelection(result: GeneratedImage) {
    this.selectedResult = result;
  }

  changeImagen3Model(model: Imagen3Model) {
    this.selectedModel = model.value;
    this.searchTerm({model: this.selectedModel});
  }

  previewDocument(event: any, document: any) {
    event.stopPropagation();
    if (document.link.endsWith('.pdf') || document.link.endsWith('.docx')) {
      this.selectedDocument = document;
      this.safeUrl = this.sanitizer.bypassSecurityTrustResourceUrl(
        this.selectedDocument.link
      );
    }
  }

  closePreview() {
    this.selectedDocument = undefined;
  }

  ngOnDestroy() {
    this.destroyed.next();
    this.destroyed.complete();
  }

  get pagedDocuments() {
    const startIndex = this.currentPage * this.pageSize;
    return this.documents.slice(startIndex, startIndex + this.pageSize);
  }

  get totalPages() {
    return Math.ceil(this.documents.length / this.pageSize);
  }

  nextPage() {
    if (this.currentPage < this.totalPages - 1) {
      this.currentPage++;
    }
  }

  prevPage() {
    if (this.currentPage > 0) {
      this.currentPage--;
    }
  }

  onNumberOfResultsChange(event: Event) {
    this.selectedNumberOfResults =
      Number((event.target as HTMLInputElement).value) || 0;
  }

  selectStyle(event: MatButtonToggleChange) {
    this.selectedStyle = event.value;
  }

  onSliderChange(event: Event) {
    this.selectedMaskDistilation =
      Number((event.target as HTMLInputElement).value) || 0;
  }

  submitChanges() {
    this.searchTerm({
      term: this.searchRequest.term,
      model: this.selectedModel,
      imageStyle: this.selectedStyle,
      numberOfResults: this.selectedNumberOfResults,
      maskDistilation: this.selectedMaskDistilation,
    });
  }
}
