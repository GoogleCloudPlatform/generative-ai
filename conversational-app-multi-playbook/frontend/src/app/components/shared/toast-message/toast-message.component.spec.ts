import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ToastMessageComponent } from './toast-message.component';

describe('ToastMessageComponent', () => {
  let component: ToastMessageComponent;
  let fixture: ComponentFixture<ToastMessageComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ToastMessageComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ToastMessageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
