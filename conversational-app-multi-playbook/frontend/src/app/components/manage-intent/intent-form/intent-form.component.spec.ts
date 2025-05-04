import {ComponentFixture, TestBed} from '@angular/core/testing';

import {IntentFormComponent} from './intent-form.component';

describe('IntentFormComponent', () => {
  let component: IntentFormComponent;
  let fixture: ComponentFixture<IntentFormComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [IntentFormComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(IntentFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
