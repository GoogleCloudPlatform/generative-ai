import { ApplicationConfig, InjectionToken, importProvidersFrom } from '@angular/core';
import { provideRouter } from '@angular/router';
import { HttpClientModule } from '@angular/common/http';

import { routes } from './app.routes';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';

export const BASE_URL = new InjectionToken<string>('BASE_URL');

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes), provideAnimationsAsync(),
    {
      provide: BASE_URL,
      useValue: '/api'
    },
    importProvidersFrom(HttpClientModule),
  ]
};
