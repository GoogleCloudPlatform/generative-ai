import { Component, OnDestroy } from '@angular/core';
import { UserService } from 'src/app/services/user/user.service';
import { Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { AddAgentBuilderComponent } from '../agent-builder/add-agent-builder/add-agent-builder.component';
import { ConfigurationService } from 'src/app/services/configuration.service';
import {ReplaySubject} from 'rxjs';
import {  takeUntil, switchMap
} from 'rxjs/operators';
import { SearchResponse } from 'src/app/models/search.model';

@Component({
  selector: 'app-main',
  templateUrl: './main.component.html',
  styleUrls: ['./main.component.scss'],
})
export class MainComponent implements OnDestroy {
  private readonly destroyed = new ReplaySubject<void>(1);
  term: string = '';
  showResults: boolean = false;
  searchResults: SearchResponse
  savedUser;

  constructor(
    public userService: UserService,
    private router: Router,
    public dialog: MatDialog,
    private readonly configService : ConfigurationService,
  ) {
    this.savedUser = userService.getUserDetails();
    this.checkConfiguration();
  }

  checkConfiguration(){
    this.configService.getConfiguration().pipe(takeUntil(this.destroyed)).subscribe((config)=>{
      if(config.length == 0){
        this.openAddAgentBuilderConfigForm();
      }
    });
  }

  goToResults(term: string) {
    this.router.navigate(['/search'], { queryParams: { q: term }});
  }

  openAddAgentBuilderConfigForm(){
    this.dialog.open(AddAgentBuilderComponent,
      { disableClose: true,
        height: '600px',
        width: '1120px'
    });
  }

  ngOnDestroy() {
    this.destroyed.next();
    this.destroyed.complete();
  }

}
