import { TestBed } from '@angular/core/testing';

import { EnginesService } from './engines.service';

describe('EnginesService', () => {
  let service: EnginesService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(EnginesService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
