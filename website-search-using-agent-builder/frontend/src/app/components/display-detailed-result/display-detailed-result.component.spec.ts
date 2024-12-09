import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DisplayDetailedResultComponent } from './display-detailed-result.component';

describe('DisplayDetailedResultComponent', () => {
  let component: DisplayDetailedResultComponent;
  let fixture: ComponentFixture<DisplayDetailedResultComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ DisplayDetailedResultComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(DisplayDetailedResultComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
