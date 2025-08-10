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
