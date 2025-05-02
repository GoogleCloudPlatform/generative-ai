import {Injectable} from '@angular/core';
import {BehaviorSubject} from 'rxjs';

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

  constructor() {}

  showLoading() {
    this.loadingSubject.next(true);
  }

  hideLoading() {
    this.loadingSubject.next(false);
  }

  getUserDetails(): UserStored {
    if (localStorage.getItem('USER_DETAILS') !== null) {
      const userObj = localStorage.getItem('USER_DETAILS');
      return JSON.parse(userObj || '{}');
    } else {
      const userDetails: UserStored = {};
      return userDetails;
    }
  }
}
