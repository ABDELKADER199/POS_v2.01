// مقتطف مبدئي لخدمة المصادقة في Angular
import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tap } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class AuthService {
  apiUrl = '/api';
  tokenKey = 'api_token';
  constructor(private http: HttpClient) {}

  login(credentials: {email: string, password: string}){
    return this.http.post<any>(`${this.apiUrl}/login`, credentials)
      .pipe(tap(res => {
        if (res.token) localStorage.setItem(this.tokenKey, res.token);
      }));
  }

  logout(){
    const token = localStorage.getItem(this.tokenKey);
    return this.http.post(`${this.apiUrl}/logout`, {}, { headers: { Authorization: `Bearer ${token}` } })
      .pipe(tap(()=> localStorage.removeItem(this.tokenKey)));
  }

  getToken(){
    return localStorage.getItem(this.tokenKey);
  }
}
