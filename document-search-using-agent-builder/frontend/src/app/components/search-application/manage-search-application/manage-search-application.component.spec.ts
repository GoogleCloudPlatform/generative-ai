import {ComponentFixture, TestBed} from '@angular/core/testing';

import {ManageSearchApplicationComponent} from './manage-search-application.component';

describe('ManageAgentBuilderComponent', () => {
  let component: ManageSearchApplicationComponent;
  let fixture: ComponentFixture<ManageSearchApplicationComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ManageSearchApplicationComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ManageSearchApplicationComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
