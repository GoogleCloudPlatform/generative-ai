import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AddAgentBuilderComponent } from './add-agent-builder.component';

describe('AddAgentBuilderComponent', () => {
  let component: AddAgentBuilderComponent;
  let fixture: ComponentFixture<AddAgentBuilderComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ AddAgentBuilderComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AddAgentBuilderComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
