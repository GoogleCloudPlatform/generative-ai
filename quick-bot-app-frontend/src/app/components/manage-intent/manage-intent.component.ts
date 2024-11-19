import { Component, ViewChild, TemplateRef, OnDestroy } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { IntentService, IntentDetails, Model } from '../../services/intent.service';
import { ToastMessageComponent } from '../shared/toast-message/toast-message.component';
import { MatSnackBar } from '@angular/material/snack-bar';
import { takeUntil, ReplaySubject, take } from 'rxjs';
import { FormGroup, FormBuilder, FormArray, FormControl, Validators } from "@angular/forms";
import { MatDialogRef } from '@angular/material/dialog';
import { ModelsService } from 'src/app/services/models.service';

@Component({
  selector: 'app-manage-intent',
  templateUrl: './manage-intent.component.html',
  styleUrls: ['./manage-intent.component.scss']
})
export class ManageIntentComponent implements OnDestroy {

  showSpinner: boolean[] = [];
  showSavedSectionSpinner: boolean[] = [];
  showMainSpinner = false;
  showDialogSpinner = false;
  models: Model[] = [];
  gcsPath: boolean[] = [];

  @ViewChild('deleteDialogRef', { static: true })
  deleteDialogRef!: TemplateRef<{}>;

  deleteIntentDialogRef?: MatDialogRef<{}>;

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
    private readonly dialog: MatDialog,
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

  addSavedIntentSection(intent: IntentDetails, i: number) {
    this.disabledSavedIntentList[i] = true;
    const form = this.getSavedIntentForm(intent, i);
    this.savedIntentSectionQuestionList[i] = 0;
    this.savedIntentSectionQuestionIndexList[i.toString()] = [i + '_0'];
    for (let q = 1; q < intent.questions.length; q++) {
      this.savedIntentSectionQuestionIndexList[i.toString()].push(i + '_' + q);
      form.addControl('question_' + i + '_' + q, new FormControl(intent.questions[q], [Validators.required]));
      this.savedIntentSectionQuestionList[i]++;
    }
    form.disable();
    const intentSection = this.savedIntentSectionForm.get('intentSection') as FormArray;
    intentSection.push(form);
    this.savedIntentSectionList.push(this.savedIntentCount);
    this.savedIntentCount++;
  }

  addQuestionField(i: number) {
    const intentSection = this.intentSectionForm.get('intentSection') as FormArray;
    const form = intentSection.at(i) as FormGroup;
    this.intentSectionQuestionIndexList[i.toString()].push(i + '_' + (this.intentSectionQuestionList[i] + 1));
    form.addControl('question_' + i + '_' + (this.intentSectionQuestionList[i] + 1), new FormControl('', Validators.required));
    this.intentSectionQuestionList[i]++;
  }

  addQuestionFieldInSavedIntent(i: number) {
    const intentSection = this.savedIntentSectionForm.get('intentSection') as FormArray;
    const form = intentSection.at(i) as FormGroup;
    this.savedIntentSectionQuestionIndexList[i.toString()].push(i + '_' + (this.savedIntentSectionQuestionList[i] + 1));
    form.addControl('question_' + i + '_' + (this.savedIntentSectionQuestionList[i] + 1), new FormControl('', Validators.required));
    this.savedIntentSectionQuestionList[i]++;
  }


  getAllIntent() {
    this.showMainSpinner = true;
    this.intentService.getAllIntent().pipe(takeUntil(this.destroyed)).subscribe({
      next: (response) => {
        this.showMainSpinner = false;
        this.handleIntent(response);
      },
      error: () => {
        this.showMainSpinner = false;
        console.log('error');
      }
    });
  }

  handleIntent(intentList: IntentDetails[]) {
    for (let i = 0; i < intentList.length; i++) {
      this.addSavedIntentSection(intentList[i], i);
    }
  }

  ngOnDestroy() {
    this.destroyed.next();
    this.destroyed.complete();
  }

  protected syntaxHighlight(json: string) {
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
      var cls = 'number';
      if (/^"/.test(match)) {
        if (/:$/.test(match)) {
          cls = 'key';
        } else {
          cls = 'string';
        }
      } else if (/true|false/.test(match)) {
        cls = 'boolean';
      } else if (/null/.test(match)) {
        cls = 'null';
      }
      return '<span class="' + cls + '">' + match + '</span>';
    });
  }

  createRange(i: number) {
    return i == 0 ? [0] : [...Array(i).keys(), i];
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
      ai_temperature: 1,
      description: intentDetailsForm.get('description_' + i)?.value,
      prompt: intentDetailsForm.get('prompt_' + i)?.value,
      questions: this.getQuestionsList(intentDetailsForm, i),
      status: "1",
    };
    this.showSpinner[i] = true;
    this.disableIntentForm(i);
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

  updateIntent(event: any, i: number) {
    event.stopPropagation();
    console.log(this.savedIntentSectionQuestionIndexList);
    const intentSection = this.savedIntentSectionForm.get('intentSection') as FormArray;
    const intentDetailsForm = intentSection.at(i) as FormGroup;
    const reqObj: IntentDetails = {
      name: intentDetailsForm.get('intent_' + i)?.value,
      gcp_bucket: intentDetailsForm.get('gcp_bucket_' + i)?.value,
      ai_model: intentDetailsForm.get('ai_model_' + i)?.value,
      ai_temperature: intentDetailsForm.get('ai_temperature' + i)?.value,
      description: intentDetailsForm.get('description_' + i)?.value,
      prompt: intentDetailsForm.get('prompt_' + i)?.value,
      questions: this.getSavedIntentQuestionList(intentDetailsForm, i),
      status: intentDetailsForm.get('status' + i)?.value,
    };
    this.showSavedSectionSpinner[i] = true;
    this.intentService.updateIntent(reqObj)
      .pipe(takeUntil(this.destroyed))
      .subscribe({
        next: () => {
          this.showSavedSectionSpinner[i] = false;
          this.disableSavedIntentForm(i);
          this.discardIntentSection(i);
          this._snackBar.openFromComponent(ToastMessageComponent, {
            panelClass: ["green-toast"],
            verticalPosition: "top",
            horizontalPosition: "right",
            duration: 5000,
            data: { text: 'Intent Saved', icon: "tick-with-circle" },
          });
        },
        error: () => {
          this.showSavedSectionSpinner[i] = false;
          this._snackBar.openFromComponent(ToastMessageComponent, {
            panelClass: ["red-toast"],
            verticalPosition: "top",
            horizontalPosition: "right",
            duration: 5000,
            data: { text: 'failed to save intent', icon: "cross-in-circle-white" },
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

  getSavedIntentQuestionList(intentDetails: FormGroup, i: number): string[] {
    const question = [];
    for (const questionIndex of this.savedIntentSectionQuestionIndexList[i]) {
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

  removeSavedIntentQuestionField(i: number, j: string) {
    const intentSection = this.savedIntentSectionForm.get('intentSection') as FormArray;
    const form = intentSection.at(i) as FormGroup;
    form.removeControl('question_' + j);
    this.savedIntentSectionQuestionIndexList[i] = this.savedIntentSectionQuestionIndexList[i].filter((x: string) => x != j);
  }

  discardSavedIntentSection(i: number) {
    this.showDialogSpinner = true;
    const intentSection = this.savedIntentSectionForm.get('intentSection') as FormArray;
    const intentDetailsForm = intentSection.at(i) as FormGroup;
    const name = intentDetailsForm.get('intent_' + i)?.value;
    this.intentService.deleteIntent(name).pipe(takeUntil(this.destroyed)).subscribe({
      next: () => {
        this.showDialogSpinner = false;
        this.deleteIntentDialogRef?.close();
        intentSection.removeAt(i);
        this.savedIntentSectionQuestionList[i] = 0;
        this.savedIntentCount--;
        this._snackBar.openFromComponent(ToastMessageComponent, {
          panelClass: ["green-toast"],
          verticalPosition: "top",
          horizontalPosition: "right",
          duration: 5000,
          data: { text: 'Intent deleted', icon: "tick-with-circle" },
        });
      },
      error: () => {
        this.showDialogSpinner = false;
        this._snackBar.openFromComponent(ToastMessageComponent, {
          panelClass: ["red-toast"],
          verticalPosition: "top",
          horizontalPosition: "right",
          duration: 5000,
          data: { text: 'failed to delete intent', icon: "cross-in-circle-white" },
        });

      }
    });
  }

  showDeleteIntentDialog(event: any, i: number) {
    event.stopPropagation();
    this.deleteIntentDialogRef = this.dialog.open(this.deleteDialogRef, { data: i, width: '60%', maxWidth: '700px' });
  }

  enableSavedIntent(event: any, i: number) {
    event.stopPropagation();
    this.disabledSavedIntentList[i] = false;
    const intentSection = this.savedIntentSectionForm.get('intentSection') as FormArray;
    const form = intentSection.at(i) as FormGroup;
    form.enable();
    form.get('intent_' + i)?.disable();
    form.get('gcp_bucket_' + i)?.disable();

  }

  disableSavedIntentForm(i: number) {
    this.disabledSavedIntentList[i] = true;
    const intentSection = this.savedIntentSectionForm.get('intentSection') as FormArray;
    const form = intentSection.at(i) as FormGroup;
    form.disable();
  }

  disableIntentForm(i: number) {
    const intentSection = this.intentSectionForm.get('intentSection') as FormArray;
    const form = intentSection.at(i) as FormGroup;
    form.disable();
  }

  getHumanReadablestring(s: string) {
    return s.replace("_", " ").replace(/(^\w{1})|(\s+\w{1})/g, letter => letter.toUpperCase());
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

