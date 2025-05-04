import {ComponentFixture, TestBed} from '@angular/core/testing';

import {CreateIntentFormComponent} from './create-intent-form.component';

describe('CreateIntentFormComponent', () => {
  let component: CreateIntentFormComponent;
  let fixture: ComponentFixture<CreateIntentFormComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [CreateIntentFormComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(CreateIntentFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
