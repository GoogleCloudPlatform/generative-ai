import { Component, NgZone, inject } from '@angular/core';
import { Auth, signInWithPopup, GoogleAuthProvider } from '@angular/fire/auth';
import { Router } from '@angular/router';
import { AuthService } from 'src/app/services/login/auth.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ToastMessageComponent } from '../shared/toast-message/toast-message.component';
import { environment } from 'src/environments/environment';

const HOME_ROUTE = '/'

interface LooseObject {
  [key: string]: any
}

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent {
  private readonly auth: Auth = inject(Auth);
  private readonly provider: GoogleAuthProvider = new GoogleAuthProvider();
  loader: boolean = false;
  chatbotName: string = environment.chatbotName;

  constructor(private authService: AuthService,
    private router: Router,
    public ngZone: NgZone,
    private _snackBar: MatSnackBar,
  ) {
    this.provider.setCustomParameters({
      prompt: "select_account"
    });
  }


  loginWithGoogle() {
    this.loader = true;
    signInWithPopup(this.auth, this.provider)
      .then((result: any) => {
        const user = result.user.toJSON();
        this.ngZone.run(() => {
          this.authService.saveUserSession(user.stsTokenManager.accessToken);
          this.redirect(user);
        });
      }).catch((error) => {
        this.loader = false;
        if (error.message !== "Firebase: Error (auth/popup-closed-by-user).") {
          this._snackBar.openFromComponent(ToastMessageComponent, {
            panelClass: ["red-toast"],
            verticalPosition: "top",
            horizontalPosition: "right",
            duration: 5000,
            data: { text: "Error with SignIn. Please try again later !!!", icon: "cross-in-circle-white" },
          });
        }
        console.error(`Error: ${error}`);
      });
  }

  redirect(user: any) {
    let userDetails: LooseObject = {}
    userDetails['name'] = user.displayName
    userDetails['email'] = user.email
    userDetails['photoURL'] = user.photoURL
    userDetails['domain'] = user.domain
    userDetails['uid'] = user.uid,
    localStorage.setItem('USER_DETAILS', JSON.stringify(userDetails));
    this.loader = false;
    this.router.navigate([HOME_ROUTE]);
  }
}
