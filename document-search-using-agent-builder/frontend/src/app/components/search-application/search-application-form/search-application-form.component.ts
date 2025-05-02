import {Component} from '@angular/core';
import {MatDialogRef} from '@angular/material/dialog';
import {Router} from '@angular/router';
import {Engine} from 'src/app/models/engine.model';
import {EnginesService} from 'src/app/services/engines.service';
import {SearchApplicationService} from 'src/app/services/search_application.service';
import {UserService} from 'src/app/services/user/user.service';

@Component({
  selector: 'app-search-application-form',
  templateUrl: './search-application-form.component.html',
  styleUrls: ['./search-application-form.component.scss'],
})
export class SearchApplicationFormComponent {
  showSpinner = false;
  selectedEngine: Engine;
  engines: Engine[] = [];

  constructor(
    private dialogRef: MatDialogRef<SearchApplicationFormComponent>,
    private readonly router: Router,
    private readonly searchApplicationService: SearchApplicationService,
    private userService: UserService,
    private enginesService: EnginesService
  ) {
    this.enginesService
      .getAll()
      .subscribe(response => (this.engines = response));
  }

  saveForm() {
    if (this.selectedEngine) {
      const searchApplication = {
        engine_id: this.selectedEngine.engine_id,
        region: this.selectedEngine.region,
      };
      this.userService.showLoading();
      this.searchApplicationService.create(searchApplication).subscribe({
        next: () => {
          this.userService.hideLoading();
          this.dialogRef.close()!;
          this.router.navigateByUrl('/');
        },
        error: () => {
          this.userService.hideLoading();
        },
      });
    }
  }
}
