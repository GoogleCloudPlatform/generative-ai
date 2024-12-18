import { TestBed } from '@angular/core/testing';

import { SearchApplicationService } from './search_application.service';

describe('SearchApplicationService', () => {
  let service: SearchApplicationService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(SearchApplicationService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
