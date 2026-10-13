import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class AdminService {
  private apiUrl = '/api/admin';

  constructor(private http: HttpClient) {}

  // Categories
  getCategories(): Observable<any[]> { return this.http.get<any[]>(`${this.apiUrl}/categories`, { withCredentials: true }); }
  createCategory(data: any): Observable<any> { return this.http.post<any>(`${this.apiUrl}/categories`, data, { withCredentials: true }); }
  updateCategory(id: number, data: any): Observable<any> { return this.http.put<any>(`${this.apiUrl}/categories/${id}`, data, { withCredentials: true }); }
  deleteCategory(id: number): Observable<any> { return this.http.delete<any>(`${this.apiUrl}/categories/${id}`, { withCredentials: true }); }

  // Products
  getProducts(page: number = 1, search: string = ''): Observable<any> { 
      return this.http.get<any>(`${this.apiUrl}/products`, { params: { page: page.toString(), search }, withCredentials: true }); 
  }
  createProduct(data: any): Observable<any> { return this.http.post<any>(`${this.apiUrl}/products`, data, { withCredentials: true }); }
  updateProduct(id: number, data: any): Observable<any> { return this.http.put<any>(`${this.apiUrl}/products/${id}`, data, { withCredentials: true }); }
  deleteProduct(id: number): Observable<any> { return this.http.delete<any>(`${this.apiUrl}/products/${id}`, { withCredentials: true }); }

  // Inventory
  getInventory(page: number = 1, search: string = ''): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/inventory`, { params: { page: page.toString(), search, store_id: '1' }, withCredentials: true });
  }
  adjustInventory(payload: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/inventory/adjust`, payload, { withCredentials: true });
  }

  // Inventory Count
  getCountStores(): Observable<any[]> { return this.http.get<any[]>(`${this.apiUrl}/inventory-count/stores`, { withCredentials: true }); }
  getCountSessions(status: string = '', storeId: string = ''): Observable<any[]> {
    let params: any = {};
    if (status) params.status = status;
    if (storeId) params.store_id = storeId;
    return this.http.get<any[]>(`${this.apiUrl}/inventory-count/sessions`, { params, withCredentials: true });
  }
  createCountSession(data: any): Observable<any> { return this.http.post<any>(`${this.apiUrl}/inventory-count/sessions`, data, { withCredentials: true }); }
  getCountSessionItems(sessionId: number, search: string = ''): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/inventory-count/sessions/${sessionId}/items`, { params: { search }, withCredentials: true });
  }
  updateCountItem(sessionId: number, itemId: number, data: any): Observable<any> {
    return this.http.put<any>(`${this.apiUrl}/inventory-count/sessions/${sessionId}/items/${itemId}`, data, { withCredentials: true });
  }
  approveCountSession(sessionId: number): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/inventory-count/sessions/${sessionId}/approve`, {}, { withCredentials: true });
  }

  // Suppliers
  getSuppliers(): Observable<any[]> { return this.http.get<any[]>(`${this.apiUrl}/suppliers`, { withCredentials: true }); }
  createSupplier(data: any): Observable<any> { return this.http.post<any>(`${this.apiUrl}/suppliers`, data, { withCredentials: true }); }
  
  // Purchases
  createPurchase(data: any): Observable<any> { return this.http.post<any>(`${this.apiUrl}/purchases`, data, { withCredentials: true }); }

  // Accounts & Treasury
  getAccountsSummary(): Observable<any> { return this.http.get<any>(`${this.apiUrl}/accounts/summary`, { withCredentials: true }); }
  getExpenses(): Observable<any> { return this.http.get<any>(`${this.apiUrl}/accounts/expenses`, { withCredentials: true }); }
  storeExpense(data: any): Observable<any> { return this.http.post<any>(`${this.apiUrl}/accounts/expenses`, data, { withCredentials: true }); }
  storeTreasuryAdjustment(data: any): Observable<any> { return this.http.post<any>(`${this.apiUrl}/accounts/treasury`, data, { withCredentials: true }); }
  getLedger(): Observable<any[]> { return this.http.get<any[]>(`${this.apiUrl}/accounts/ledger`, { withCredentials: true }); }

  // Transfers
  getTransferStores(): Observable<any[]> { return this.http.get<any[]>(`${this.apiUrl}/transfers/stores`, { withCredentials: true }); }
  getTransfers(status: string = 'All'): Observable<any[]> { return this.http.get<any[]>(`${this.apiUrl}/transfers`, { params: { status }, withCredentials: true }); }
  createTransfer(data: any): Observable<any> { return this.http.post<any>(`${this.apiUrl}/transfers`, data, { withCredentials: true }); }
  receiveTransfer(id: number): Observable<any> { return this.http.post<any>(`${this.apiUrl}/transfers/${id}/receive`, {}, { withCredentials: true }); }
  cancelTransfer(id: number): Observable<any> { return this.http.post<any>(`${this.apiUrl}/transfers/${id}/cancel`, {}, { withCredentials: true }); }

  // Call Center
  getCallCenterStores(): Observable<any[]> { return this.http.get<any[]>(`${this.apiUrl}/callcenter/stores`, { withCredentials: true }); }
  searchCallCenterProducts(term: string): Observable<any[]> { return this.http.get<any[]>(`${this.apiUrl}/callcenter/products`, { params: { term }, withCredentials: true }); }
  getCallCenterCustomer(phone: string): Observable<any> { return this.http.get<any>(`${this.apiUrl}/callcenter/customer`, { params: { phone }, withCredentials: true }); }
  createCallCenterOrder(data: any): Observable<any> { return this.http.post<any>(`${this.apiUrl}/callcenter/orders`, data, { withCredentials: true }); }
  getCallCenterOrders(status: string = 'Pending', storeId = ''): Observable<any[]> {
    let params: any = { status };
    if (storeId) params.store_id = storeId;
    return this.http.get<any[]>(`${this.apiUrl}/callcenter/orders`, { params, withCredentials: true });
  }
  updateOrderCallCenterStatus(id: number, status: string): Observable<any> { return this.http.patch<any>(`${this.apiUrl}/callcenter/orders/${id}/status`, { status }, { withCredentials: true }); }

  // Promotions
  getPromotions(): Observable<any[]> { return this.http.get<any[]>(`${this.apiUrl}/promotions`, { withCredentials: true }); }
  createPromotion(data: any): Observable<any> { return this.http.post<any>(`${this.apiUrl}/promotions`, data, { withCredentials: true }); }
  updatePromotion(id: number, data: any): Observable<any> { return this.http.put<any>(`${this.apiUrl}/promotions/${id}`, data, { withCredentials: true }); }
  deletePromotion(id: number): Observable<any> { return this.http.delete<any>(`${this.apiUrl}/promotions/${id}`, { withCredentials: true }); }
  togglePromotion(id: number): Observable<any> { return this.http.post<any>(`${this.apiUrl}/promotions/${id}/toggle`, {}, { withCredentials: true }); }
  searchPromotionProducts(term: string): Observable<any[]> { return this.http.get<any[]>(`${this.apiUrl}/promotions/search-products`, { params: { term }, withCredentials: true }); }

  // Stats Dashboard
  getDashboard(dateFrom: string, dateTo: string, storeId = ''): Observable<any> {
    let params: any = { date_from: dateFrom, date_to: dateTo };
    if (storeId) params.store_id = storeId;
    return this.http.get<any>(`${this.apiUrl}/stats/dashboard`, { params, withCredentials: true });
  }
  getStatsStores(): Observable<any[]> { return this.http.get<any[]>(`${this.apiUrl}/stats/stores`, { withCredentials: true }); }

  // Settings
  getSettings(): Observable<any> { return this.http.get<any>(`${this.apiUrl}/settings`, { withCredentials: true }); }
  updateSettings(data: any): Observable<any> { return this.http.put<any>(`${this.apiUrl}/settings`, data, { withCredentials: true }); }

  // Users & Roles
  getRoles(): Observable<any[]> { return this.http.get<any[]>(`${this.apiUrl}/roles`, { withCredentials: true }); }

  getUsers(): Observable<any[]> { return this.http.get<any[]>(`${this.apiUrl}/users`, { withCredentials: true }); }
  createUser(data: any): Observable<any> { return this.http.post<any>(`${this.apiUrl}/users`, data, { withCredentials: true }); }
  updateUser(id: number, data: any): Observable<any> { return this.http.put<any>(`${this.apiUrl}/users/${id}`, data, { withCredentials: true }); }
  deleteUser(id: number): Observable<any> { return this.http.delete<any>(`${this.apiUrl}/users/${id}`, { withCredentials: true }); }
}
