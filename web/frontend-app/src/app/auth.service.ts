import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { tap } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class AuthService {
  apiUrl = '/api';
  tokenKey = 'api_token';
  userKey = 'api_user';
  constructor(private http: HttpClient, private router: Router) {}

  login(credentials: {email: string, password: string}){
    return this.http.post<any>(`${this.apiUrl}/login`, credentials)
      .pipe(tap(res => {
        if (res.token) {
          localStorage.setItem(this.tokenKey, res.token);
          localStorage.setItem(this.userKey, JSON.stringify(res.user));
        }
      }));
  }

  logout(){
    return this.http.post<any>(`${this.apiUrl}/logout`, {}).pipe(tap(()=>{
      localStorage.removeItem(this.tokenKey);
      localStorage.removeItem(this.userKey);
      this.router.navigate(['/login']);
    }));
  }

  getToken(){
    return localStorage.getItem(this.tokenKey);
  }

  isAuthenticated(){
    return !!this.getToken();
  }

  getUser(){
    const u = localStorage.getItem(this.userKey);
    return u ? JSON.parse(u) : null;
  }
}
