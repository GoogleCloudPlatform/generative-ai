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

import { Injectable } from '@angular/core';

interface LooseObject {
  [key:string]: any
}

type UserStored = {
  uid?: string,
  name?: string,
  email?: string,
  photoURL?: string,
  displayName?: string,
  domain?: string
}

@Injectable({
  providedIn: 'root'
})
export class UserService {

  constructor() { }

  setUserDetails(userStored: UserStored) {

  }

  getUserDetails(): UserStored{
    if(localStorage.getItem('USER_DETAILS') != null){
      let userObj = localStorage.getItem("USER_DETAILS")
      return JSON.parse(userObj || '{}')
    }
    else{
      let userDetails: UserStored = {}
      return userDetails
    }
  }

}
