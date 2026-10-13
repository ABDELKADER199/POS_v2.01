import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../admin.service';
import { Router, RouterModule } from '@angular/router';

@Component({
  selector: 'app-purchases-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './purchases.component.html',
  styleUrls: ['./purchases.component.scss']
})
export class PurchasesAdminComponent implements OnInit {
  suppliers: any[] = [];
  products: any[] = [];
  
  purchase = {
      supplier_id: null as any,
      ref_number: '',
      items: [] as any[],
      paid_amount: 0,
      payment_method: 'cash'
  };

  tempItem = { product_id: null, quantity: 1, unit_cost: 0 };

  constructor(private adminApi: AdminService, public router: Router) {}

  ngOnInit() {
      this.adminApi.getSuppliers().subscribe({
        next: (res) => {
          const unwrapped = (res as any).data || res;
          this.suppliers = Array.isArray(unwrapped) ? unwrapped : (unwrapped.data || []);
          if (this.suppliers.length === 0) {
             this.adminApi.createSupplier({ name: 'مورد عام', phone: '01000' }).subscribe(ns => {
                 this.suppliers.push(ns);
                 this.purchase.supplier_id = ns.id;
             });
          } else {
             this.purchase.supplier_id = this.suppliers[0].id;
          }
        }
      });

      this.adminApi.getProducts(1, '').subscribe({
        next: (res) => {
          const unwrapped = (res as any).data || res;
          this.products = unwrapped.data || unwrapped || [];
        }
      });
  }

  getProductName(id: number) {
      const p = this.products.find(x => x.id == id);
      return p ? p.product_name : 'غير معروف';
  }

  addItem() {
      if (!this.tempItem.product_id || this.tempItem.quantity <= 0 || this.tempItem.unit_cost < 0) {
          return alert('بيانات الصنف غير صحيحة');
      }
      this.purchase.items.push({...this.tempItem});
      this.tempItem = { product_id: null, quantity: 1, unit_cost: 0 };
  }

  removeItem(index: number) {
      this.purchase.items.splice(index, 1);
  }

  getTotal() {
      return this.purchase.items.reduce((acc: number, it: any) => acc + (it.quantity * it.unit_cost), 0);
  }

  submitPurchase() {
      if (!this.purchase.supplier_id) return alert('برجاء اختيار مورد');
      
      const payload = {
          supplier_id: this.purchase.supplier_id,
          ref_number: this.purchase.ref_number,
          paid_amount: this.purchase.paid_amount,
          payment_method: this.purchase.payment_method,
          items: this.purchase.items
      };

      if (!confirm(`سيتم حفظ الفاتورة وإضافة البضاعة للمخزن وتوثيق الدفع / الدين، هل تكمل؟`)) return;

      this.adminApi.createPurchase(payload).subscribe({
          next: () => {
              alert('تم تسجيل فاتورة المشتريات وإضافة البضاعة بنجاح');
              this.purchase.items = [];
              this.purchase.ref_number = '';
              this.purchase.paid_amount = 0;
          },
          error: err => alert(err.error?.error || err.error?.message || 'حدث خطأ أثناء حفظ الفاتورة')
      });
  }
}

