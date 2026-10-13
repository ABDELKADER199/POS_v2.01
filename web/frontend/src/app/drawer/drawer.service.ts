import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class DrawerService {
  constructor(private http: HttpClient) {}
  getStatus() { return this.http.get<any>('/api/drawer/status', { withCredentials: true }); }
  open(opening_balance: number) { return this.http.post<any>('/api/drawer/open', { opening_balance }, { withCredentials: true }); }
  close(drawer_id: number, closing_balance: number) { return this.http.post<any>('/api/drawer/close', { drawer_id, closing_balance }, { withCredentials: true }); }
}
