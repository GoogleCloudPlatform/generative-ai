import {ComponentFixture, TestBed} from '@angular/core/testing';

import {SearchApplicationFormComponent} from './search-application-form.component';

describe('AddAgentBuilderComponent', () => {
  let component: SearchApplicationFormComponent;
  let fixture: ComponentFixture<SearchApplicationFormComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [SearchApplicationFormComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(SearchApplicationFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
