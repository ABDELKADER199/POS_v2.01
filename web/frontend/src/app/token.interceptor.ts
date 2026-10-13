import { HttpHandler, HttpInterceptor, HttpRequest } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { environment } from '../environments/environment';
import { AuthService } from './auth.service';

@Injectable()
export class TokenInterceptor implements HttpInterceptor {
  constructor(private auth: AuthService) {}

  intercept(req: HttpRequest<any>, next: HttpHandler) {
    let outgoing = req;

    if (!req.url.startsWith('http')) {
      outgoing = req.clone({ url: `${environment.apiBase}${req.url}` });
    }

    const xsrfToken = this.getXsrfToken();
    if (xsrfToken && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(req.method.toUpperCase())) {
      outgoing = outgoing.clone({
        withCredentials: true,
        setHeaders: { 'X-XSRF-TOKEN': xsrfToken }
      });
    } else {
      outgoing = outgoing.clone({ withCredentials: true });
    }

    return next.handle(outgoing);
  }

  private getXsrfToken(): string | null {
    const cookie = document.cookie
      .split('; ')
      .find((row) => row.startsWith('XSRF-TOKEN='));

    if (!cookie) {
      return null;
    }

    const value = cookie.split('=')[1];
    return value ? decodeURIComponent(value) : null;
  }
}
