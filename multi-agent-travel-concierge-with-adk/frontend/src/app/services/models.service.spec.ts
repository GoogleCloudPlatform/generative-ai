import { TestBed } from '@angular/core/testing';

import { ModelsService } from './models.service';

describe('ModelsService', () => {
  let service: ModelsService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ModelsService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
