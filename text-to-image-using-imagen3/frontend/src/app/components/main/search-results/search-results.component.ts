import {Component, OnDestroy, ViewChild, TemplateRef} from '@angular/core';
import {SearchService} from 'src/app/services/search.service';
import {ReplaySubject} from 'rxjs';
import {UserService} from 'src/app/services/user/user.service';
import {ActivatedRoute, Router} from '@angular/router';
import {PDF, image_name} from 'src/environments/constant';
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

interface Imagen3Model {
  value: string;
  viewValue: string;
}

interface AspectRatio {
  value: string;
  viewValue: string;
}
interface Style {
  value: string;
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
  searchResult: any = [];
  isLoading = false;
  documents: any = [];
  showDefaultDocuments = false;
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
  selectedImageStyle = 'Modern';
  currentSearchTerm = '';
  numberOfResults = 4;
  imagen3ModelsList: Imagen3Model[] = [
    {value: 'imagen-3.0-generate-001', viewValue: 'imagen-3.0-generate-001'},
    {
      value: 'imagen-3.0-fast-generate-001',
      viewValue: 'imagen-3.0-fast-generate-001',
    },
    {value: 'imagen-3.0-generate-002', viewValue: 'imagen-3.0-generate-002'},
    {value: 'imagegeneration@006', viewValue: 'imagegeneration@006'},
    {value: 'imagegeneration@005', viewValue: 'imagegeneration@005'},
    {value: 'imagegeneration@002', viewValue: 'imagegeneration@002'},
  ];
  selectedModel = this.imagen3ModelsList[0].value;
  aspectRatioList: AspectRatio[] = [
    {value: '1:1', viewValue: '1:1'},
    {value: '9:16', viewValue: '9:16'},
    {value: '16:9', viewValue: '16:9'},
    {value: '2:4', viewValue: '2:4'},
    {value: '4:1', viewValue: '4:1'},
  ];
  selectedAspectRatio = this.aspectRatioList[0];
  searchRequest: SearchRequest = {
    term: '',
    model: this.selectedModel,
    aspectRatio: this.selectedAspectRatio.value,
    imageStyle: this.selectedImageStyle,
    numberOfImages: this.numberOfResults,
  };
  imageStyleList: Style[] = [
    {value: 'Modern'},
    {value: 'Realistic'},
    {value: 'Vintage'},
    {value: 'Monochrome'},
    {value: 'Fantasy'},
  ];
  activatedRoute: ActivatedRoute | null | undefined;

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
    this.currentSearchTerm = query;
    const newSearchRequest = this.searchRequest;

    this.service.search(newSearchRequest).subscribe({
      next: (searchResponse: GeneratedImage[]) => {
        this.summary = searchResponse?.[0]?.enhancedPrompt || '';
        this.documents = searchResponse;
        this.searchResult.forEach((element: GeneratedImage) => {
          this.images.push(element.image?.encodedImage);
        });
        this.selectedResult = searchResponse[0];

        this.userService.hideLoading();
      },
      error: error => {
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
        this.showErrorSnackBar(error);
      },
    });
  }

  showErrorSnackBar(error: any): void {
    console.error('Search error:', error);
    console.error('Search typeof error:', typeof error);
    console.error('Search error?.message:', error?.message);
    console.error(
      'Search typeof JSON.stringify:',
      JSON.stringify(error, null, 2)
    );

    let errorMessage = '';
    if (error?.error?.detail?.[0]?.msg)
      errorMessage = `${error?.error?.detail?.[0]?.msg} - ${error?.error?.detail?.[0]?.loc}`;
    else if (error?.error?.detail)
      if (
        error.error.detail.includes(
          "The image you want to edit contains content that has been blocked because you selected the 'Don't allow' option for Person Generation."
        )
      ) {
        errorMessage =
          'The image you want to edit contains content that has been blocked because there are persons in it. See the safety settings documentation for more details.';
      } else errorMessage = error?.error?.detail;
    else 'Error sending request. Please try again later!';

    this._snackBar.openFromComponent(ToastMessageComponent, {
      panelClass: ['red-toast'],
      verticalPosition: 'top',
      horizontalPosition: 'right',
      duration: 10000,
      data: {
        text: errorMessage,
        icon: 'cross-in-circle-white',
      },
    });
  }

  goToResults(term: string) {
    this.router.navigate(['/search'], {queryParams: {q: term}});
  }

  searchTerm({
    term,
    aspectRatio,
    model,
    imageStyle,
    numberOfImages,
  }: {
    term?: string | undefined;
    aspectRatio?: string | undefined;
    model?: string | undefined;
    imageStyle?: string | undefined;
    numberOfImages?: number | undefined;
  }) {
    if (!term) return;

    this.showDefaultDocuments = false;
    this.userService.showLoading();
    this.searchResult = [];
    this.summary = '';
    this.documents = [];
    this.images = [];

    this.searchRequest.term = term || this.searchRequest.term;
    this.searchRequest.aspectRatio =
      aspectRatio || this.selectedAspectRatio.value;
    this.searchRequest.model = model || this.selectedModel;
    this.searchRequest.imageStyle = imageStyle || this.selectedImageStyle;
    this.searchRequest.numberOfImages = numberOfImages || this.numberOfResults;

    const newSearchRequest = this.searchRequest;
    console.log('Search request:', newSearchRequest);
    this.currentSearchTerm = newSearchRequest.term;

    this.service.search(newSearchRequest).subscribe({
      next: (searchResponse: any) => {
        this.summary = searchResponse?.[0]?.enhancedPrompt || '';
        this.documents = searchResponse;
        this.searchResult.forEach((element: GeneratedImage) => {
          this.images.push(element.image?.encodedImage);
        });
        this.selectedResult = searchResponse[0];
        this.userService.hideLoading();
        console.log('Search response:', searchResponse);
      },
      error: error => {
        console.error('Search error:', error);
        this.userService.hideLoading();
        this.showErrorSnackBar(error);
      },
    });

    this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: {q: this.currentSearchTerm},
      queryParamsHandling: '',
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

  changeAspectRatio(aspectRatio: AspectRatio) {
    this.selectedAspectRatio = aspectRatio;
    this.searchTerm({aspectRatio: aspectRatio.value});
    console.log('Selected Aspect Ratio:', this.selectedAspectRatio);
  }

  changeImageStyle(style: Style) {
    this.selectedImageStyle = style.value;
    console.log('Selected Image Style:', this.selectedImageStyle);
  }

  onNumberOfResultsChange(event: any) {
    this.numberOfResults = event.target.value;
    console.log('Selected Number of Results:', this.numberOfResults);
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
}
