import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DialogueBoxComponent } from './dialogue-box.component';

describe('DialogueBoxComponent', () => {
  let component: DialogueBoxComponent;
  let fixture: ComponentFixture<DialogueBoxComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ DialogueBoxComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(DialogueBoxComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
