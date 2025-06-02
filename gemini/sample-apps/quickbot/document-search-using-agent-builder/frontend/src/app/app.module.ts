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

import {NgModule} from '@angular/core';
import {BrowserModule} from '@angular/platform-browser';
import {AppRoutingModule} from './app-routing.module';
import {AppComponent} from './app.component';
import {HeaderComponent} from './components/header/header.component';
import {FooterComponent} from './components/footer/footer.component';
import {MainComponent} from './components/main/main.component';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {MatIconModule} from '@angular/material/icon';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatButtonModule} from '@angular/material/button';
import {MatToolbarModule} from '@angular/material/toolbar';
import {HttpClientModule} from '@angular/common/http';
import {MatInputModule} from '@angular/material/input';
import {NgFor, PathLocationStrategy} from '@angular/common';
import {MatSelectModule} from '@angular/material/select';
import {MatFormFieldModule} from '@angular/material/form-field';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatGridListModule} from '@angular/material/grid-list';
import {MatCardModule} from '@angular/material/card';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatTooltipModule} from '@angular/material/tooltip';
import {LoginComponent} from './components/login/login.component';
import {initializeApp, provideFirebaseApp} from '@angular/fire/app';
import {
  provideAnalytics,
  getAnalytics,
  ScreenTrackingService,
  UserTrackingService,
} from '@angular/fire/analytics';
import {environment} from '../environments/environment';
import {provideAuth, getAuth} from '@angular/fire/auth';
import {MatMenuModule} from '@angular/material/menu';
import {MatDividerModule} from '@angular/material/divider';
import {MatChipsModule} from '@angular/material/chips';
import {LocationStrategy} from '@angular/common';
import {MarkdownModule} from 'ngx-markdown';
import {MatDialogModule} from '@angular/material/dialog';
import {CdkAccordionModule} from '@angular/cdk/accordion';
import {MatExpansionModule} from '@angular/material/expansion';
import {IonicRatingModule} from 'ionic-emoji-rating';
import {MatListModule} from '@angular/material/list';
import {MatTabsModule} from '@angular/material/tabs';
import {MatTableModule} from '@angular/material/table';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatSlideToggleModule} from '@angular/material/slide-toggle';
import {MatButtonToggleModule} from '@angular/material/button-toggle';
import {MatSnackBarModule} from '@angular/material/snack-bar';
import {MatSortModule} from '@angular/material/sort';
import {MatPaginatorModule} from '@angular/material/paginator';
import {MatSidenavModule} from '@angular/material/sidenav';
import {NgIdleModule} from '@ng-idle/core';
import {ClipboardModule} from '@angular/cdk/clipboard';
import {MatProgressBarModule} from '@angular/material/progress-bar';
import {ManageSearchApplicationComponent} from './components/search-application/manage-search-application/manage-search-application.component';
import {SearchApplicationFormComponent} from './components/search-application/search-application-form/search-application-form.component';
import {PdfViewerModule} from 'ng2-pdf-viewer';

import 'prismjs';
import 'prismjs/components/prism-typescript.min.js';
import 'prismjs/plugins/line-numbers/prism-line-numbers.js';
import 'prismjs/plugins/line-highlight/prism-line-highlight.js';
import {FlexLayoutModule} from '@angular/flex-layout';
import {MatSliderModule} from '@angular/material/slider';
import {MatStepperModule} from '@angular/material/stepper';
import {ChatInputComponent} from './components/main/chat-input/chat-input.component';
import {SearchResultsComponent} from './components/main/search-results/search-results.component';
import {ToastMessageComponent} from './components/toast-message/toast-message.component';
import {TruncatePipe} from './pipes/truncate.pipe';

@NgModule({
  declarations: [
    AppComponent,
    HeaderComponent,
    FooterComponent,
    MainComponent,
    LoginComponent,
    ChatInputComponent,
    SearchResultsComponent,
    ToastMessageComponent,
    SearchApplicationFormComponent,
    ManageSearchApplicationComponent,
    TruncatePipe,
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    BrowserAnimationsModule,
    MatSnackBarModule,
    MatPaginatorModule,
    MatSortModule,
    MatSliderModule,
    MatToolbarModule,
    MatButtonModule,
    MatIconModule,
    HttpClientModule,
    FormsModule,
    MatFormFieldModule,
    MatSelectModule,
    NgFor,
    MatInputModule,
    MatGridListModule,
    MatCardModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
    MatMenuModule,
    MatDividerModule,
    MatChipsModule,
    ReactiveFormsModule,
    MatMenuModule,
    MatDialogModule,
    CdkAccordionModule,
    IonicRatingModule,
    MarkdownModule.forRoot(),
    MatExpansionModule,
    MatListModule,
    MatTabsModule,
    MatCheckboxModule,
    MatTableModule,
    MatSlideToggleModule,
    MatButtonToggleModule,
    MatSidenavModule,
    MatAutocompleteModule,
    environment.requiredLogin === 'True'
      ? [
          provideFirebaseApp(() => initializeApp(environment.firebase)),
          provideAuth(() => getAuth()),
        ]
      : [],
    environment.requiredLogin === 'True'
      ? [provideAnalytics(() => getAnalytics())]
      : [],
    FlexLayoutModule,
    NgIdleModule.forRoot(),
    ClipboardModule,
    MatStepperModule,
    MatProgressBarModule,
    PdfViewerModule,
  ],
  providers: [
    {provide: LocationStrategy, useClass: PathLocationStrategy},
    environment.requiredLogin === 'True'
      ? [
          ScreenTrackingService, // Automatically track screen views
          UserTrackingService, // Automatically track user interactions
        ]
      : [],
  ],
  bootstrap: [AppComponent],
})
export class AppModule {}
