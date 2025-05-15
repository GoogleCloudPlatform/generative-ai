import { Component } from '@angular/core';
import { UserService } from 'src/app/services/user/user.service';

@Component({
  selector: 'app-chat',
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.scss']
})
export class ChatComponent {
  userInfo:any;

  constructor(
    private userService: UserService
  ) {
    this.userInfo = this.userService.getUserDetails();
  }
}
