import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../admin.service';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-callcenter-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './callcenter.component.html',
  styleUrls: ['./callcenter.component.scss']
})
export class CallCenterAdminComponent implements OnInit {
  activeTab = 'new_order';
  stores: any[] = [];
  
  // New Order State
  searchQuery = '';
  searchResults: any[] = [];
  cart: any[] = [];
  customerPhone = '';
  customerName = '';
  customerAddress = '';
  targetStoreId: number | null = null;
  searchTimeout: any;

  // Pending/Completed
  pendingOrders: any[] = [];
  completedOrders: any[] = [];
  storeFilter = '';

  constructor(private adminApi: AdminService) {}

  ngOnInit() {
    this.adminApi.getCallCenterStores().subscribe(res => {
        const unwrapped = (res as any).data || res;
        this.stores = Array.isArray(unwrapped) ? unwrapped : (unwrapped.data || []);
        if(this.stores.length > 0) this.targetStoreId = this.stores[0].id;
    });
    this.loadPending();
  }

  setTab(tab: string) {
    this.activeTab = tab;
    if (tab === 'pending') this.loadPending();
    if (tab === 'completed') this.loadCompleted();
  }

  // --- Logic for New Order
  onSearchInput() {
    if (this.searchTimeout) clearTimeout(this.searchTimeout);
    this.searchTimeout = setTimeout(() => {
        if (!this.searchQuery || this.searchQuery.length < 2) {
            this.searchResults = [];
            return;
        }
        this.adminApi.searchCallCenterProducts(this.searchQuery).subscribe(res => {
            const unwrapped = (res as any).data || res;
            this.searchResults = Array.isArray(unwrapped) ? unwrapped : (unwrapped.data || []);
        });
    }, 300);
  }

  onPhoneChange() {
      if (this.customerPhone.length >= 10 && this.customerPhone.length <= 11) {
          this.adminApi.getCallCenterCustomer(this.customerPhone).subscribe(res => {
              const cust = (res as any).data || res;
              if (cust && !Array.isArray(cust)) {
                  this.customerName = cust.name || cust.customer_name || '';
                  this.customerAddress = cust.address || '';
              }
          });
      }
  }

  addToCart(product: any) {
      const existing = this.cart.find(c => c.product_id === product.id);
      if (existing) {
          existing.quantity++;
      } else {
          this.cart.push({
              product_id: product.id,
              name: product.product_name,
              code: product.product_code,
              price: product.sell_price,
              quantity: 1
          });
      }
  }

  removeFromCart(index: number) {
      this.cart.splice(index, 1);
  }

  get cartTotal() {
      return this.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  }

  submitOrder() {
      if (this.cart.length === 0) return alert('اللة سلة المشتريات فارغة');
      if (!this.customerName || !this.customerPhone || !this.targetStoreId) return alert('برجاء استكمال بيانات العميل واسم الفرع');
      
      const payload = {
          customer_name: this.customerName,
          customer_phone: this.customerPhone,
          customer_address: this.customerAddress,
          target_store_id: this.targetStoreId,
          items: this.cart.map(c => ({ product_id: c.product_id, quantity: c.quantity, price: c.price }))
      };

      if (confirm('تأكيد إنشاء الطلب وإرساله للفرع المحدد للتسليم؟')) {
          this.adminApi.createCallCenterOrder(payload).subscribe({
              next: (res: any) => {
                  const unw = res.data || res;
                  alert(unw.message + '\nرقم الطلب: ' + unw.order_number);
                  this.cart = [];
                  this.customerName = '';
                  this.customerPhone = '';
                  this.customerAddress = '';
                  this.searchQuery = '';
                  this.searchResults = [];
              },
              error: err => alert(err.error?.message || 'حدث خطأ')
          });
      }
  }

  // --- Logic for Viewing
  loadPending() {
      this.adminApi.getCallCenterOrders('Pending', this.storeFilter).subscribe(res => {
          const unwrapped = (res as any).data || res;
          this.pendingOrders = Array.isArray(unwrapped) ? unwrapped : (unwrapped.data || []);
      });
  }

  loadCompleted() {
      this.adminApi.getCallCenterOrders('Completed', this.storeFilter).subscribe(res => {
          const unwrapped = (res as any).data || res;
          this.completedOrders = Array.isArray(unwrapped) ? unwrapped : (unwrapped.data || []);
      });
  }

  changeStatus(orderId: number, status: string) {
      if(confirm(`تأكيد تغيير حالة الطلب إلى "${status}"؟`)) {
          this.adminApi.updateOrderCallCenterStatus(orderId, status).subscribe(() => {
              this.loadPending();
              this.loadCompleted();
          });
      }
  }
}
