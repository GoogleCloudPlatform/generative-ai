import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';
import {MainComponent} from './components/main/main.component';
import {LoginComponent} from './components/login/login.component';
import {AuthGuard} from './services/login/auth.guard';
import {SearchResultsComponent} from './components/main/search-results/search-results.component';
import {ManageSearchApplicationComponent} from './components/search-application/manage-search-application/manage-search-application.component';

const routes: Routes = [
  {path: '', component: MainComponent, canActivate: [AuthGuard]},
  {path: 'login', component: LoginComponent},
  {path: 'search', component: SearchResultsComponent, canActivate: [AuthGuard]},
  // TODO: Add new AddNewAgentComponent
  {
    path: 'manage-config',
    component: ManageSearchApplicationComponent,
    canActivate: [AuthGuard],
  },
];

@NgModule({
  imports: [RouterModule.forRoot(routes, {onSameUrlNavigation: 'reload'})],
  exports: [RouterModule],
})
export class AppRoutingModule {}
