import {Component} from '@angular/core';
import {
  IntentService,
  IntentDetails,
  Model,
} from '../../services/intent.service';
import {ModelsService} from 'src/app/services/models.service';

@Component({
  selector: 'app-manage-intent',
  templateUrl: './manage-intent.component.html',
  styleUrls: ['./manage-intent.component.scss'],
})
export class ManageIntentComponent {
  intents: IntentDetails[];
  showMainSpinner = false;
  models: Model[] = [];
  createMode = false;

  constructor(
    private intentService: IntentService,
    private modelsService: ModelsService
  ) {
    this.getAllIntent();
    this.modelsService.getAll().subscribe(response => {
      this.models = response;
    });
  }

  getAllIntent() {
    this.showMainSpinner = true;
    this.intentService.getAllIntent().subscribe({
      next: response => {
        this.showMainSpinner = false;
        this.intents = response;
      },
      error: () => {
        this.showMainSpinner = false;
        console.log('error');
      },
    });
  }

  enterCreateMode() {
    this.createMode = true;
  }

  exitCreateMode() {
    this.createMode = false;
  }
}
