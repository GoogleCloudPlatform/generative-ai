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

import {Component, OnDestroy, ViewChild, TemplateRef} from '@angular/core';
import {SearchService} from 'src/app/services/search.service';
import {ReplaySubject} from 'rxjs';
import {UserService} from 'src/app/services/user/user.service';
import {ActivatedRoute, Router} from '@angular/router';
import {PDF, image_name} from 'src/environments/constant';
import {
  SafeUrl,
} from '@angular/platform-browser';
import {CombinedImageResults, GeneratedImage} from 'src/app/models/generated-image.model';
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
  imagenDocuments: GeneratedImage[] = [];
  geminiDocuments: GeneratedImage[] = [];
  showDefaultDocuments = false;
  defaultPlaceholderImageUrl = 'assets/images/placeholder_image.png';
  images: any = [];
  pdf = PDF;
  imageName = image_name;
  safeUrl: SafeUrl | undefined;
  selectedResult: GeneratedImage | undefined;
  selectedImageStyle = 'Modern';
  currentSearchTerm = '';
  numberOfResults = 2;
  imagen3ModelsList: Imagen3Model[] = [
    {value: 'imagen-4.0-ultra-generate-exp-05-20', viewValue: 'Imagen 4.0-ultra-generate-exp-05-20'},
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
    {value: '3:4', viewValue: '3:4'},
    {value: '4:3', viewValue: '4:3'},
  ];
  selectedAspectRatio = this.aspectRatioList[0];
  searchRequest: SearchRequest = {
    term: '',
    generationModel: this.selectedModel,
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
    {value: 'Sketch'},
  ];
  activatedRoute: ActivatedRoute | null | undefined;

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private service: SearchService,
    private userService: UserService,
    private _snackBar: MatSnackBar
  ) {
    const query = this.route.snapshot.queryParamMap.get('q');
    this.userService.showLoading();

    if (!query) {
      this.selectedResult = undefined;
      this.showDefaultDocuments = true;
      this.userService.hideLoading();
      return;
    }

    this.searchRequest.term = query || '';
    this.currentSearchTerm = query;
    const newSearchRequest = this.searchRequest;

    this.service.search(newSearchRequest).subscribe({
      next: (searchResponse: CombinedImageResults) => {
        this.processSearchResults(searchResponse);
        this.userService.hideLoading();
      },
      error: error => {
        this.handleSearchError(error)
      },
    });
  }

  private handleSearchError(error: any) {
    console.error('Search error:', error);
    this.imagenDocuments = [];
    this.geminiDocuments = [];
    this.selectedResult = undefined;
    this.showDefaultDocuments = true;
    this.summary = 'An error occurred while generating images.';
    this.userService.hideLoading();
    this.showErrorSnackBar(error);
  }

  private processSearchResults(searchResponse: CombinedImageResults) {
    this.imagenDocuments = (searchResponse.imagenResults || []).map(img => ({
      ...img,
      source: 'Imagen Model',
    }));
    this.geminiDocuments = (searchResponse.geminiResults || []).map(img => ({
      ...img,
      source: 'Gemini 2.0 Model',
    }));

    const hasImagenResults = this.imagenDocuments.length > 0;
    const hasGeminiResults = this.geminiDocuments.length > 0;

    if (hasImagenResults || hasGeminiResults) {
      this.showDefaultDocuments = false;
      this.selectedResult = hasImagenResults ? this.imagenDocuments[0] : this.geminiDocuments[0];
      this.summary = this.selectedResult?.enhancedPrompt || 'Image generation results displayed.';
    } else {
      this.showDefaultDocuments = true;
      this.selectedResult = undefined;
      this.summary = 'No images were generated for your prompt.';
    }
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
    this.imagenDocuments = [];
    this.geminiDocuments = [];
    this.images = [];

    this.searchRequest.term = term || this.searchRequest.term;
    this.searchRequest.aspectRatio =
      aspectRatio || this.selectedAspectRatio.value;
    this.searchRequest.generationModel = model || this.selectedModel;
    this.searchRequest.imageStyle = imageStyle || this.selectedImageStyle;
    this.searchRequest.numberOfImages = numberOfImages || this.numberOfResults;

    const newSearchRequest = this.searchRequest;
    console.log('Search request:', newSearchRequest);
    this.currentSearchTerm = newSearchRequest.term;

    this.service.search(newSearchRequest).subscribe({
      next: (searchResponse: CombinedImageResults) => {
        this.processSearchResults(searchResponse);
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

  changeImageSelection(result: GeneratedImage) {
    this.selectedResult = result;
    this.summary = result.enhancedPrompt || '';
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

  ngOnDestroy() {
    this.destroyed.next();
    this.destroyed.complete();
  }
}
