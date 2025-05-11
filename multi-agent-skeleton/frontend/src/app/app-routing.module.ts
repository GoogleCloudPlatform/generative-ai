import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ChatComponent } from './components/main/chat/chat.component';
import { MainComponent } from './components/main/main.component';
import { LoginComponent } from './components/login/login.component';
import { AuthGuard } from './services/login/auth.guard';

const routes: Routes = [
  {path: '', component: MainComponent, canActivate: [AuthGuard]},
  {path: 'login', component: LoginComponent},
  {path: 'chat', component: ChatComponent, canActivate: [AuthGuard]},
];


@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
