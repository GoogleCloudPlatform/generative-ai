import { Component, OnDestroy } from '@angular/core';
import { IntentService, IntentDetails, Model } from '../../services/intent.service';
import { ToastMessageComponent } from '../shared/toast-message/toast-message.component';
import { MatSnackBar } from '@angular/material/snack-bar';
import { takeUntil, ReplaySubject } from 'rxjs';
import { FormGroup, FormBuilder, FormArray, FormControl, Validators } from "@angular/forms";
import { ModelsService } from 'src/app/services/models.service';

@Component({
  selector: 'app-manage-intent',
  templateUrl: './manage-intent.component.html',
  styleUrls: ['./manage-intent.component.scss']
})
export class ManageIntentComponent implements OnDestroy {

  intents: IntentDetails[];
  showSpinner: boolean[] = [];
  showSavedSectionSpinner: boolean[] = [];
  showMainSpinner = false;
  showDialogSpinner = false;
  models: Model[] = [];
  gcsPath: boolean[] = [];

  private readonly destroyed = new ReplaySubject<void>(1);
  interval: any;

  // new intents
  intentSectionList: number[] = [];
  intentSectionQuestionList: number[] = [];
  intentSectionQuestionIndexList: any = {};
  savedIntentSectionQuestionIndexList: any = {};
  intentCount: number = 0;
  intentSectionForm = new FormGroup({
    'intentSection': this.fb.array([])
  });

  // saved Intent Section
  savedIntentSectionList: number[] = [];
  savedIntentSectionQuestionList: number[] = [];
  savedIntentCount: number = 0;
  savedIntentSectionForm = new FormGroup({
    'intentSection': this.fb.array([])
  });
  disabledSavedIntentList: boolean[] = [];
  showGCSField = false;

  createMode: boolean = false;

  getNewForm(i: number) {
    const form = new FormGroup({});
    form.addControl('intent_' + i, new FormControl('', Validators.required));
    form.addControl('gcp_bucket_' + i, new FormControl('', Validators.required));
    form.addControl('ai_model_' + i, new FormControl('', Validators.required));
    form.addControl('description_' + i, new FormControl('', Validators.required));
    form.addControl('prompt_' + i, new FormControl('', Validators.required));
    form.addControl('question_' + i + '_0', new FormControl('', Validators.required));
    this.gcsPath[i] = false;
    return form;
  }

  getSavedIntentForm(intent: IntentDetails, i: number) {
    const form = new FormGroup({});
    const intentFormControl = new FormControl(intent.name);
    intentFormControl.disable()
    const bucketFormControl = new FormControl(intent.gcp_bucket);
    bucketFormControl.disable()
    const aiModelFormControl = new FormControl(intent.ai_model);
    aiModelFormControl.setValue(intent.ai_model);
    form.addControl('intent_' + i, intentFormControl);
    form.addControl('gcp_bucket_' + i, bucketFormControl);
    form.addControl('ai_model_' + i, aiModelFormControl);
    form.addControl('description_' + i, new FormControl(intent.description, Validators.required));
    form.addControl('prompt_' + i, new FormControl(intent.prompt, Validators.required));
    form.addControl('question_' + i + '_0', new FormControl(intent.questions[0], Validators.required));
    form.addControl('status_' + i, new FormControl(intent.status, Validators.required));

    return form;
  }


  constructor(
    private intentService: IntentService,
    private _snackBar: MatSnackBar,
    private fb: FormBuilder,
    private modelsService: ModelsService,
  ) {
    this.getAllIntent();
    this.modelsService.getAll().subscribe(response => {
      this.models = response;
    });
    this.fetchIntentDataAtIntervals();
  }

  getAllIntent() {
    this.showMainSpinner = true;
    this.intentService.getAllIntent().pipe(takeUntil(this.destroyed)).subscribe({
      next: (response) => {
        this.showMainSpinner = false;
        this.intents = response;
      },
      error: () => {
        this.showMainSpinner = false;
        console.log('error');
      }
    });
  }

  enterCreateMode() {
    this.createMode = true;
  }

  exitCreateMode() {
    this.createMode = false;
  }

  get getFormArray(): FormArray {
    return this.intentSectionForm.get('intentSection') as FormArray;
  }

  get getSavedFormArray(): FormArray {
    return this.savedIntentSectionForm.get('intentSection') as FormArray;
  }

  addIntentSection() {
    const intentSection = this.intentSectionForm.get('intentSection') as FormArray;
    intentSection.push(this.getNewForm(this.intentCount));
    this.intentSectionList.push(this.intentCount);
    this.intentSectionQuestionList[this.intentCount] = 0;
    this.intentSectionQuestionIndexList[this.intentCount.toString()] = [this.intentCount + '_0'];
    this.intentCount++;
  }

  addQuestionField(i: number) {
    const intentSection = this.intentSectionForm.get('intentSection') as FormArray;
    const form = intentSection.at(i) as FormGroup;
    this.intentSectionQuestionIndexList[i.toString()].push(i + '_' + (this.intentSectionQuestionList[i] + 1));
    form.addControl('question_' + i + '_' + (this.intentSectionQuestionList[i] + 1), new FormControl('', Validators.required));
    this.intentSectionQuestionList[i]++;
  }


  ngOnDestroy() {
    this.destroyed.next();
    this.destroyed.complete();
  }

  discardIntentSection(i: number) {
    const intentSection = this.intentSectionForm.get('intentSection') as FormArray;
    intentSection.removeAt(i);
    this.intentSectionQuestionList[i] = 0;
    this.intentCount--;
  }

  saveIntent(event: any, i: number) {
    event.stopPropagation();
    const intentSection = this.intentSectionForm.get('intentSection') as FormArray;
    const intentDetailsForm = intentSection.at(i) as FormGroup;
    let name: string = intentDetailsForm.get('intent_' + i)?.value;

    const reqObj: IntentDetails = {
      name: name.toLocaleLowerCase().replaceAll(" ", "_"),
      gcp_bucket: intentDetailsForm.get('gcp_bucket_' + i)?.value,
      ai_model: intentDetailsForm.get('ai_model_' + i)?.value,
      ai_temperature: "1",
      description: intentDetailsForm.get('description_' + i)?.value,
      prompt: intentDetailsForm.get('prompt_' + i)?.value,
      questions: this.getQuestionsList(intentDetailsForm, i),
      status: "1",
    };
    this.showSpinner[i] = true;
    this.intentService.saveIntent(reqObj)
      .pipe(takeUntil(this.destroyed))
      .subscribe({
        next: () => {
          this.showSpinner[i] = false;
          this.discardIntentSection(i);
          this._snackBar.openFromComponent(ToastMessageComponent, {
            panelClass: ["green-toast"],
            verticalPosition: "top",
            horizontalPosition: "right",
            duration: 5000,
            data: { text: 'Intent Saved', icon: "tick-with-circle" },
          });
          window.location.reload()
        },
        error: (response) => {
          const message = response.error && response.error.detail ? response.error.detail : "Error creating intent"
          this.showSpinner[i] = false;
          this._snackBar.openFromComponent(ToastMessageComponent, {
            panelClass: ["red-toast"],
            verticalPosition: "top",
            horizontalPosition: "right",
            duration: 5000,
            data: { text: message, icon: "cross-in-circle-white" },
          });

        }
      });
  }

  getQuestionsList(intentDetails: FormGroup, i: number): string[] {
    const question = [];
    for (const questionIndex of this.intentSectionQuestionIndexList[i]) {
      question.push(intentDetails.get('question_' + questionIndex)?.value);
    }
    return question;
  }


  removeQuestionField(i: number, j: string) {
    const intentSection = this.intentSectionForm.get('intentSection') as FormArray;
    const form = intentSection.at(i) as FormGroup;
    form.removeControl('question_' + j);
    this.intentSectionQuestionIndexList[i] = this.intentSectionQuestionIndexList[i].filter((x: string) => x != j);
  }

  openGCSPathTutorial() {
    window.open("https://screenshot.googleplex.com/3Nih9dZaj3z82T3.png")
  }

  showGSCPath(i: number) { }

  fetchIntentDataAtIntervals() {
    this.interval = setInterval(()=>{this.getAllIntentStatus();}, 300000);
  }

  getAllIntentStatus(){
    this.intentService.getAllIntent().pipe(takeUntil(this.destroyed)).subscribe({
      next: (response) => {
        this.handleAllIntentStatus(response);
      },
      error: () => {
        console.log('error');
      }
    });
  }

  handleAllIntentStatus(intentList: IntentDetails[]){
    for (let i = 0; i < intentList.length; i++) {
      if(intentList[i].status !== "5") {
        const intentSection = this.intentSectionForm.get('intentSection') as FormArray;
        const form = intentSection.at(i) as FormGroup;
        form.addControl('status_' + i, new FormControl(intentList[i].status, Validators.required));
      }
    }
  }
}

