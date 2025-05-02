import {Injectable} from '@angular/core';
import {BehaviorSubject} from 'rxjs';
import {environment} from 'src/environments/environment';

type UserStored = {
  uid?: string;
  name?: string;
  email?: string;
  photoURL?: string;
  displayName?: string;
  domain?: string;
};

@Injectable({
  providedIn: 'root',
})
export class UserService {
  readonly loadingSubject = new BehaviorSubject<boolean>(false);
  requiredLogin: string = environment.requiredLogin;

  constructor() {}

  setUserDetails(userStored: UserStored) {}

  showLoading() {
    this.loadingSubject.next(true);
  }

  hideLoading() {
    this.loadingSubject.next(false);
  }

  getUserDetails(): UserStored {
    if (
      this.requiredLogin === 'True' &&
      localStorage.getItem('USER_DETAILS') !== null
    ) {
      const userObj = localStorage.getItem('USER_DETAILS');
      return JSON.parse(userObj || '{}');
    } else {
      const userDetails: UserStored = {};
      return userDetails;
    }
  }
}
