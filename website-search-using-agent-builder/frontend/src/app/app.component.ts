import { Component } from '@angular/core';
import { Router, NavigationEnd, Event as NavigationEvent } from '@angular/router';
import { UserService } from './services/user/user.service';
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

  constructor(
    private router: Router,
    private userService: UserService,
    public authService: AuthService,
  ) {
    this.router.events.subscribe(
      (event: NavigationEvent) => {
        if (event instanceof NavigationEnd) {
          if (event.url == '/login' || event.url == '/login/e2e' || (event.url.includes('login') && event.url.includes('email')) || (event.url.includes('login') && event.url.includes('tos')) || event.url.includes('reset-password') || event.url.includes('support-ticket')) {
            this.showHeader = false
          }
          else {
            this.userInfo = this.userService.getUserDetails();
            this.showHeader = true;
          }
        }
      });
  }
}
