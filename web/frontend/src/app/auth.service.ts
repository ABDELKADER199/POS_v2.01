import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, map, switchMap, tap } from 'rxjs';

interface LoginResponse {
  user: any;
  step?: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private apiUrl = '/api';
  private currentUser: any = null;
  private permissionNames: string[] = [];
  private featureKeys: string[] = [];

  constructor(private http: HttpClient, private router: Router) {}

  login(credentials: { email: string; password: string }): Observable<LoginResponse> {
    return this.http.get<any>('/sanctum/csrf-cookie', { withCredentials: true }).pipe(
      switchMap(() => {
        const xsrfToken = this.getXsrfToken();
        const requestOptions: { withCredentials: boolean; headers?: Record<string, string> } = {
          withCredentials: true,
        };

        if (xsrfToken) {
          requestOptions.headers = { 'X-XSRF-TOKEN': xsrfToken };
        }

        return this.http.post<LoginResponse>(`${this.apiUrl}/login`, credentials, requestOptions);
      }),
      tap((res) => {
        if (res?.user) {
          this.currentUser = res.user;
          this.syncPermissionCache(res.user);
        }
      })
    );
  }

  logout() {
    return this.http.post<any>(`${this.apiUrl}/logout`, {}, { withCredentials: true }).pipe(
      tap(() => {
        this.currentUser = null;
        this.permissionNames = [];
        this.featureKeys = [];
        this.router.navigate(['/login']);
      })
    );
  }

  isAuthenticated() {
    return !!this.currentUser;
  }

  getUser() {
    return this.currentUser;
  }

  loadUser(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/me`, { withCredentials: true }).pipe(
      tap((u) => {
        const user = u?.data ?? u;
        this.currentUser = user;
        this.syncPermissionCache(user);
      })
    );
  }

  loadPermissions(): Observable<string[]> {
    return this.http.get<any>(`${this.apiUrl}/permissions`, { withCredentials: true }).pipe(
      tap((res) => {
        const payload = res?.data ?? res;
        this.permissionNames = payload?.permissions ?? [];
      }),
      map(() => this.permissionNames)
    );
  }

  loadFeatures(): Observable<string[]> {
    return this.http.get<any>(`${this.apiUrl}/features`, { withCredentials: true }).pipe(
      tap((res) => {
        const payload = res?.data ?? res;
        this.featureKeys = payload?.features ?? [];
      }),
      map(() => this.featureKeys)
    );
  }

  hasPermission(name: string): boolean {
    if (!name) return true;
    if (this.permissionNames.includes(name)) return true;
    const direct = this.currentUser?.permissions;
    if (Array.isArray(direct)) {
      return direct.some((p: any) => (typeof p === 'string' ? p : p?.name) === name);
    }
    return false;
  }

  hasFeature(key: string): boolean {
    return this.featureKeys.includes(key);
  }

  private syncPermissionCache(user: any): void {
    if (!user?.permissions) return;
    this.permissionNames = user.permissions.map((p: any) => (typeof p === 'string' ? p : p.name));
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
