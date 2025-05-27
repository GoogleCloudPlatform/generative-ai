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

import { Component, ChangeDetectorRef } from '@angular/core';
import { Router, NavigationEnd, Event as NavigationEvent } from '@angular/router';
import { UserService } from './services/user/user.service';
import { Idle, DEFAULT_INTERRUPTSOURCES } from '@ng-idle/core';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { DialogueBoxComponent } from './dialogue-box/dialogue-box.component';
import { AuthService } from './services/login/auth.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent {
  title = 'pac-assist-ui';
  showHeader: boolean = true
  userInfo: any;
  ref?: MatDialogRef<DialogueBoxComponent>;

  constructor(private router: Router,
    private userService: UserService,
    private idle: Idle, cd: ChangeDetectorRef,
    public authService: AuthService,
    private dialog: MatDialog) {
    this.router.events.subscribe(
      (event: NavigationEvent) => {
        if (event instanceof NavigationEnd) {
          if (event.url == '/login' || event.url == '/login/e2e' || (event.url.includes('login') && event.url.includes('email')) || (event.url.includes('login') && event.url.includes('tos')) || event.url.includes('reset-password') || event.url.includes('support-ticket')) {
            this.showHeader = false
          }
          else {
            this.userInfo = this.userService.getUserDetails();
            this.showHeader = true;
            // idle for 2 days then show dialog
            idle.setIdle(172800);
            idle.setInterrupts(DEFAULT_INTERRUPTSOURCES);
            idle.onIdleStart.subscribe(() => {
              this.showIdleDialog();
            });
            this.idle.watch();
          }
        }
      });
  }

  showIdleDialog() {
    if(!this.ref && this.showHeader){
      const config = {
        title: "Session Idle",
        icon: "av_timer",
        description: "Session has been inactive for 48 hours, user will be logged out automatically.",
        showConfirmBtn: false,
        confirmBtnText: "logout",
        cancelCallBackFunction: () => {
          this.idle.watch();
        },
        needsExtraProcessing: true,
        extraProcessingFunction: () => {
          setTimeout(() =>{this.ref?.close();this.authService.logout();},20000);
        }
      };

      this.ref = this.dialog.open(DialogueBoxComponent, { data: config, disableClose: true });
    }
    this.ref?.afterClosed().subscribe(()=>{
      this.ref = undefined;
    });
  }
}
