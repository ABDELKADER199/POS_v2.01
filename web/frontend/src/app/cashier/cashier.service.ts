import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface Product {
  id: number;
  product_name: string;
  price: number;
  sell_price: number;
  barcode: string;
  product_code?: string;
  stock: number;
}

@Injectable({
  providedIn: 'root'
})
export class CashierService {
  private apiUrl = '/api/cashier';

  constructor(private http: HttpClient) {}

  getProducts(search: string = ''): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/products`, {
      params: { search, store_id: '1' },
      withCredentials: true
    });
  }

  scanBarcode(code: string): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/products/barcode/${code}`, { withCredentials: true });
  }

  calculateCart(items: any[]): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/cart/calculate`, { items }, { withCredentials: true });
  }

  checkout(saleData: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/sale`, saleData, { withCredentials: true });
  }

  getHeldInvoices(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/held-invoices`, { withCredentials: true });
  }

  holdInvoice(data: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/held-invoices`, data, { withCredentials: true });
  }

  deleteHeldInvoice(id: number): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/held-invoices/${id}`, { withCredentials: true });
  }
}
