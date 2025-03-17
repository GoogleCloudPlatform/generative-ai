import {ComponentFixture, TestBed} from '@angular/core/testing';

import {BackgroundChangerInputComponent} from './background-changer-input.component';

describe('BackgroundChangerComponent', () => {
  let component: BackgroundChangerInputComponent;
  let fixture: ComponentFixture<BackgroundChangerInputComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [BackgroundChangerInputComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(BackgroundChangerInputComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
