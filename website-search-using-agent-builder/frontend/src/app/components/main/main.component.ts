import { Component } from '@angular/core';
import { UserService } from 'src/app/services/user/user.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-main',
  templateUrl: './main.component.html',
  styleUrls: ['./main.component.scss'],
})
export class MainComponent {
  savedUser;

  constructor(
    public userService: UserService,
    private router: Router
  ) {
    this.savedUser = userService.getUserDetails();
  }

  goToResults(term: string) {
    this.router.navigate(['/search'], { queryParams: { q: term }});
  }
}
