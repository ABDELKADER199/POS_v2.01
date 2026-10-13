import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ReturnsService {
  constructor(private http: HttpClient) {}
  getInvoice(invoice_number: string) { return this.http.get<any>(`/api/returns/${invoice_number}`, { withCredentials: true }); }
  processReturn(payload: any) { return this.http.post<any>('/api/returns', payload, { withCredentials: true }); }
}
