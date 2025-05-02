import {Injectable} from '@angular/core';

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
  constructor() {}

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
