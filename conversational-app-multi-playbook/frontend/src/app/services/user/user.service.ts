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
