import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ManageAgentBuilderComponent } from './manage-agent-builder.component';

describe('ManageAgentBuilderComponent', () => {
  let component: ManageAgentBuilderComponent;
  let fixture: ComponentFixture<ManageAgentBuilderComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ManageAgentBuilderComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ManageAgentBuilderComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
