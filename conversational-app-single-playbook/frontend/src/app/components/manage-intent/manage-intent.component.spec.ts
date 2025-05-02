import {ComponentFixture, TestBed} from '@angular/core/testing';

import {ManageIntentComponent} from './manage-intent.component';

describe('ManageIntentComponent', () => {
  let component: ManageIntentComponent;
  let fixture: ComponentFixture<ManageIntentComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ManageIntentComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ManageIntentComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
