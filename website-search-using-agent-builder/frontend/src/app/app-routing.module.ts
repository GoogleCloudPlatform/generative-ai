import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { MainComponent } from './components/main/main.component';
import { LoginComponent } from './components/login/login.component';
import { AuthGuard } from './services/login/auth.guard';
import { ManageIntentComponent } from './components/manage-intent/manage-intent.component';
import { SearchResultComponent } from './components/search-result/search-result.component';

const routes: Routes = [
  {path: '', component: MainComponent, canActivate: [AuthGuard]},
  {path: 'login', component: LoginComponent},
  {path: 'result', component: SearchResultComponent, canActivate: [AuthGuard]},
  {path: 'intent-management', component: ManageIntentComponent, canActivate:[AuthGuard]}
];


@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
