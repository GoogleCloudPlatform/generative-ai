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
import {GeneratedImage} from 'src/app/models/generated-image.model';
import {CombinedBackgroundChangerResults, SearchRequest} from 'src/app/models/search.model';
import {MatSnackBar} from '@angular/material/snack-bar';
import {ToastMessageComponent} from '../../toast-message/toast-message.component';

interface Imagen3Model {
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
  isLoading = false;

  geminiDocuments: GeneratedImage[] = [];
  imagenEntireImageDocuments: GeneratedImage[] = [];
  imagenBackgroundDocuments: GeneratedImage[] = [];

  showDefaultDocuments = false;
  defaultPlaceholderImageUrl = 'assets/images/placeholder_image.png';
  selectedResult: GeneratedImage | undefined;
  currentSearchTerm = '';

  imagen3ModelsList: Imagen3Model[] = [
    {
      value: 'imagen-3.0-capability-001',
      viewValue: 'Imagen 3: imagen-3.0-capability-001',
    },
  ];
  selectedModel = this.imagen3ModelsList[0].value;
  selectedNumberOfResults = 2;
  selectedMaskDistilation = 0.005;

  searchRequest: SearchRequest = {
    term: '',
    model: this.selectedModel,
    numberOfResults: this.selectedNumberOfResults,
    maskDistilation: this.selectedMaskDistilation,
  };

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

    this.currentSearchTerm = query;
    const initialSearchRequest: SearchRequest = {
      term: query,
      model: this.selectedModel,
      numberOfResults: this.selectedNumberOfResults,
      maskDistilation: this.selectedMaskDistilation,
    };
    this.searchTerm(initialSearchRequest);
  }

  searchTerm({
    term,
    model,
    numberOfResults,
    maskDistilation,
  }: {
    term?: string | undefined;
    model?: string | undefined;
    numberOfResults?: number | undefined;
    maskDistilation?: number | undefined;
  }) {
    this.isLoading = true;
    this.userService.showLoading();

    this.searchRequest.term = term || this.searchRequest.term;
    this.searchRequest.model = model || this.selectedModel;
    this.searchRequest.numberOfResults = numberOfResults || this.selectedNumberOfResults;
    this.searchRequest.maskDistilation =
      maskDistilation || this.selectedMaskDistilation;
    this.currentSearchTerm = this.searchRequest.term;

    // Reset previous results
    this.geminiDocuments = [];
    this.imagenEntireImageDocuments = [];
    this.imagenBackgroundDocuments = [];
    this.selectedResult = undefined;
    this.summary = '';
    this.showDefaultDocuments = false;

    this.service.search(this.searchRequest).subscribe({
      next: (searchResponse: CombinedBackgroundChangerResults) => {
        this.processSearchResults(searchResponse);
        this.isLoading = false;
        this.userService.hideLoading();
      },
      error: error => {
        this.handleSearchError(error);
      },
    });
  }

  private processSearchResults(searchResponse: CombinedBackgroundChangerResults) {
    this.geminiDocuments = (searchResponse.geminiResults || []).map(img => ({
      ...img,
      source: 'Gemini',
    }));
    this.imagenEntireImageDocuments = (
      searchResponse.imagenEntireImgResults || []
    ).map(img => ({
      ...img,
      source: 'Imagen 3 - Entire Mode',
    }));
    this.imagenBackgroundDocuments = (
      searchResponse.imagenBackgroundImgResults || []
    ).map(img => ({
      ...img,
      source: 'Imagen 3 - Background Mode',
    }));

    const hasGeminiResults = this.geminiDocuments.length > 0;
    const hasImagenEntireResults = this.imagenEntireImageDocuments.length > 0;
    const hasImagenBackgroundResults =
      this.imagenBackgroundDocuments.length > 0;

    if (
      hasGeminiResults ||
      hasImagenEntireResults ||
      hasImagenBackgroundResults
    ) {
      this.showDefaultDocuments = false;
      // Select the first available image as the default selectedResult
      if (hasImagenBackgroundResults) {
        this.selectedResult = this.imagenBackgroundDocuments[0];
      } else if (hasImagenEntireResults) {
        this.selectedResult = this.imagenEntireImageDocuments[0];
      } else if (hasGeminiResults) {
        this.selectedResult = this.geminiDocuments[0];
      }
      this.summary =
        this.selectedResult?.enhancedPrompt ||
        'Image generation results displayed.';
    } else {
      this.showDefaultDocuments = true;
      this.selectedResult = undefined;
      this.summary = 'No images were generated for your prompt.';
    }
  }

  private handleSearchError(error: any) {
    console.error('Search error:', error);
    this.geminiDocuments = [];
    this.imagenEntireImageDocuments = [];
    this.imagenBackgroundDocuments = [];
    this.selectedResult = undefined;
    this.showDefaultDocuments = true;
    this.summary = 'An error occurred while generating images.';
    this.isLoading = false;
    this.userService.hideLoading();
    this.showErrorSnackBar(error);
  }

  showErrorSnackBar(error: any): void {
    let errorMessage = 'Error sending request. Please try again later!';
    let triedToGeneratePersons = false;

    if (error?.error?.detail) {
      if (typeof error.error.detail === 'string') {
        if (
          error.error.detail.includes(
            "The image you want to edit contains content that has been blocked because you selected the 'Don't allow' option for Person Generation."
          )
        ) {
          triedToGeneratePersons = true;
          errorMessage =
            'The image you want to edit contains content that has been blocked because there are persons in it. See the safety settings documentation for more details.';
        } else {
          errorMessage = error.error.detail;
        }
      } else if (Array.isArray(error.error.detail) && error.error.detail[0]?.msg) {
         errorMessage = `${error.error.detail[0].msg} - ${error.error.detail[0].loc?.join(', ')}`;
      }
    } else if (error?.message) {
        errorMessage = error.message;
    }


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
    if (triedToGeneratePersons) this.goToHomePage();
  }

  // goToResults(term: string) {
  //   if (term) {
  //     this.router.navigate(['/search'], {queryParams: {q: term}});
  //   }
  // }

  changeImageSelection(result: GeneratedImage) {
    this.selectedResult = result;
    this.summary = result.enhancedPrompt || '';
  }

  changeImagen3Model(model: Imagen3Model) {
    this.selectedModel = model.value;
  }

  onNumberOfResultsChange(event: Event) {
    const value = Number((event.target as HTMLInputElement).value);
    this.selectedNumberOfResults = value;
  }

  onSliderChange(event: Event) {
    const value = Number((event.target as HTMLInputElement).value);
    this.selectedMaskDistilation = value;
  }

  goToHomePage() {
    this.router.navigate(['/']);
  }

  ngOnDestroy() {
    this.destroyed.next();
    this.destroyed.complete();
  }
}
