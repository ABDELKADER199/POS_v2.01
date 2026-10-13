import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { AuthService } from './auth.service';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [HttpClientTestingModule, RouterTestingModule], providers: [AuthService] });
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => { httpMock.verify(); localStorage.clear(); });

  it('should send the Sanctum CSRF token during login', () => {
    document.cookie = 'XSRF-TOKEN=test-csrf-token; path=/';

    const mock = { user: { id: 1, name: 'Test' } };
    service.login({ email: 'a', password: 'b' }).subscribe(res => {
      expect(res.user.name).toBe('Test');
    });

    const csrfReq = httpMock.expectOne('/sanctum/csrf-cookie');
    csrfReq.flush(null);

    const loginReq = httpMock.expectOne('/api/login');
    expect(loginReq.request.headers.get('X-XSRF-TOKEN')).toBe('test-csrf-token');
    loginReq.flush(mock);
  });
});
