import { TestBed } from '@angular/core/testing';

import { IntentService } from './intent.service';

describe('IntentService', () => {
  let service: IntentService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(IntentService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
