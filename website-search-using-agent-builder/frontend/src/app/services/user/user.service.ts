import { Injectable } from '@angular/core';
import {BehaviorSubject} from 'rxjs';

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
  readonly loadingSubject = new BehaviorSubject<boolean>(false);

  constructor() { }

  setUserDetails(userStored: UserStored) {

  }

  showLoading() {
    this.loadingSubject.next(true);
  }

  hideLoading(){
    this.loadingSubject.next(false);
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
