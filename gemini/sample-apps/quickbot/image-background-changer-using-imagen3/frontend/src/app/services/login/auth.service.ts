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
import {Router} from '@angular/router';
import {environment} from 'src/environments/environment';

const USER_TOKEN_KEY = 'gpau_id';
const USER_DETAILS = 'USER_DETAILS';
const LOGIN_ROUTE = '/login';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private requiredLogin: boolean = environment.requiredLogin === 'True';

  constructor(private router: Router) {}

  saveUserSession(token: string) {
    localStorage.setItem(USER_TOKEN_KEY, token);
  }

  logout(route: string = LOGIN_ROUTE) {
    localStorage.removeItem(USER_TOKEN_KEY);
    localStorage.removeItem(USER_DETAILS);
    localStorage.removeItem('showTooltip');
    this.router.navigateByUrl(route);
  }

  isLoggedIn() {
    const isLoggedIn = localStorage.getItem(USER_TOKEN_KEY) !== null;
    if (!isLoggedIn && this.router.url !== LOGIN_ROUTE) {
      this.router.navigate([LOGIN_ROUTE]);
    }
    return isLoggedIn;
  }

  isUserLoggedIn() {
    if (!this.requiredLogin) return true;
    const isLoggedIn = localStorage.getItem(USER_TOKEN_KEY) !== null;
    return isLoggedIn;
  }
}
