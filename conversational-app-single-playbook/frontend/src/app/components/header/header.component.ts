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

import {Component} from '@angular/core';
import {DomSanitizer} from '@angular/platform-browser';
import {MatIconRegistry} from '@angular/material/icon';
import {Router} from '@angular/router';
import {UserService} from 'src/app/services/user/user.service';
import {AuthService} from '../../services/login/auth.service';
import {MatDialog} from '@angular/material/dialog';
import {environment} from 'src/environments/environment';
import {IntentDetails, IntentService} from 'src/app/services/intent.service';

const GOOGLE_CLOUD_ICON = `<svg width="694px" height="558px" viewBox="0 0 694 558" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
  <g id="Page-1" stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
      <g id="google-cloud-1" fill-rule="nonzero">
          <path d="M440.545766,152.920305 L461.717489,152.920305 L522.033632,92.9270295 L525,67.4718307 C412.772422,-31.0513593 241.450145,-20.4353843 142.396729,91.1914478 C114.856041,122.200508 94.8766816,159.08162 84,199 C90.7179504,196.251996 98.1629517,195.8181 105.171723,197.72724 L225.774927,177.941608 C225.774927,177.941608 231.911237,167.846308 235.081179,168.482688 C288.737536,109.877878 379.037259,103.051256 440.981997,152.920305 L440.545766,152.920305 Z" id="Path" fill="#EA4335"></path>
          <path d="M607.866504,200.682375 C594.001378,149.778725 565.57351,104.008948 526.012848,69 L441.426861,153.404341 C477.150633,182.525289 497.497778,226.409746 496.625757,272.440567 L496.625757,287.436115 C538.221135,287.436115 571.910193,321.081832 571.910193,362.558879 C571.910193,404.064932 538.192067,437.681644 496.625757,437.681644 L346.02782,437.681644 L331,452.880226 L331,542.998538 L346.02782,557.994086 L496.625757,557.994086 C582.955785,558.6612 659.548251,502.826713 685.185654,420.568736 C710.764921,338.281754 679.372184,248.946575 607.866504,200.682375 L607.866504,200.682375 Z" id="Path" fill="#4285F4"></path>
          <path d="M194.75446,555.998385 L346,555.998385 L346,436.702654 L194.75446,436.702654 C183.982485,436.702654 173.327279,434.43008 163.518651,430 L142.266623,436.47252 L81.3130068,496.134769 L76,517.076966 C110.184236,542.506777 151.900097,556.170985 194.75446,555.998385 L194.75446,555.998385 Z" id="Path" fill="#34A853"></path>
          <path d="M195.36137,165 C111.412398,165.496534 37.0600945,219.208571 10.2827643,298.683735 C-16.4945658,378.158899 10.1952567,465.881761 76.7302131,517 L164.383674,429.422857 C126.347031,412.257155 109.458061,367.550553 126.638723,329.547028 C143.819384,291.543502 188.564945,274.669238 226.601588,291.834941 C243.344712,299.412331 256.762546,312.818482 264.346539,329.547028 L352,241.969885 C314.692587,193.270582 256.733377,164.797082 195.36137,165 L195.36137,165 Z" id="Path" fill="#FBBC05"></path>
      </g>
  </g>
</svg>`;

@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss'],
})
export class HeaderComponent {
  headerTitle: string = environment.chatbotName;
  intentsInProgress: IntentDetails[] = [];
  requiredLogin: string = environment.requiredLogin;

  constructor(
    iconRegistry: MatIconRegistry,
    sanitizer: DomSanitizer,
    private router: Router,
    public _UserService: UserService,
    public authService: AuthService,
    public dialog: MatDialog,
    private intentsService: IntentService
  ) {
    iconRegistry.addSvgIconLiteral(
      'google-cloud-icon',
      sanitizer.bypassSecurityTrustHtml(GOOGLE_CLOUD_ICON)
    );
    this.intentsService.getAllIntent().subscribe(allIntents => {
      this.intentsInProgress = allIntents.filter(
        i => i.status === '1' || i.status === '3'
      );
    });
  }

  navigate() {
    this.router.navigateByUrl('/');
  }

  goToManageIntentPage() {
    this.router.navigateByUrl('/intent-management');
  }

  logout() {
    this.authService.logout();
  }

  openURL(link: string) {
    (window as any).open(link, '_blank');
  }
}
