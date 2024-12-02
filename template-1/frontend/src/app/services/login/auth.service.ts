import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { HttpErrorResponse } from "@angular/common/http";
import { environment } from 'src/environments/environment';
import { throwError } from "rxjs";

const USER_TOKEN_KEY = 'gpau_id'
const USER_DETAILS = 'USER_DETAILS';
const LOGIN_ROUTE = '/login'



@Injectable({
  providedIn: 'root'
})
export class AuthService {

  private requiredLogin: boolean = environment.requiredLogin == "True"

  constructor(
    private router: Router,
  ) {
  }

  saveUserSession(token: string) {
    localStorage.setItem(USER_TOKEN_KEY, token)
  }

  logout(route: string = LOGIN_ROUTE) {
    localStorage.removeItem(USER_TOKEN_KEY);
    localStorage.removeItem(USER_DETAILS);
    localStorage.removeItem('showTooltip')
    this.router.navigateByUrl(route);
  }

  isLoggedIn() {
    var isLoggedIn = localStorage.getItem(USER_TOKEN_KEY) !== null
    if (!isLoggedIn && this.router.url !== LOGIN_ROUTE) {
      this.router.navigate([LOGIN_ROUTE])
    }
    return isLoggedIn;
  }

  isUserLoggedIn(){
    if(!this.requiredLogin) return true;
    var isLoggedIn = localStorage.getItem(USER_TOKEN_KEY) !== null;
    return isLoggedIn;
  }
}
