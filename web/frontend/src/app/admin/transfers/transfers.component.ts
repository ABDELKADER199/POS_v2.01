import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../admin.service';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-transfers-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './transfers.component.html',
  styleUrls: ['./transfers.component.scss']
})
export class TransfersAdminComponent implements OnInit {
  transfers: any[] = [];
  stores: any[] = [];
  products: any[] = [];
  
  filterStatus = 'All';
  showModal = false;
  
  searchQuery = '';
  transferForm = {
     product_id: null,
     from_store_id: null,
     to_store_id: null,
     quantity: 1,
     notes: ''
  };

  constructor(private adminApi: AdminService) {}

  ngOnInit() {
    this.adminApi.getTransferStores().subscribe(res => {
        const unwrapped = (res as any).data || res;
        this.stores = Array.isArray(unwrapped) ? unwrapped : (unwrapped.data || []);
        if (this.stores.length > 0) {
           this.transferForm.from_store_id = this.stores[0].id;
           this.transferForm.to_store_id = this.stores.length > 1 ? this.stores[1].id : this.stores[0].id;
        }
    });
    this.loadData();
  }

  loadData() {
    this.adminApi.getTransfers(this.filterStatus).subscribe(res => {
        const unwrapped = (res as any).data || res;
        this.transfers = Array.isArray(unwrapped) ? unwrapped : (unwrapped.data || []);
    });
  }

  searchProducts() {
     if(!this.searchQuery) return;
     this.adminApi.getProducts(1, this.searchQuery).subscribe(res => {
        const unwrapped = (res as any).data || res;
        this.products = unwrapped.data || unwrapped || [];
        if (this.products.length > 0) {
           this.transferForm.product_id = this.products[0].id;
        }
     });
  }

  saveTransfer() {
    if (!this.transferForm.product_id || !this.transferForm.from_store_id || !this.transferForm.to_store_id) {
       return alert('برجاء استكمال كافة حقول التحويل');
    }
    if (this.transferForm.from_store_id === this.transferForm.to_store_id) {
       return alert('لا يمكن التحويل لنفس الفرع');
    }

    if (confirm('تأكيد خصم الكمية من الفرع المصدر وتحويلها؟')) {
       this.adminApi.createTransfer(this.transferForm).subscribe({
           next: (res: any) => {
               alert(res.message || 'تم تسجيل التحويل بنجاح');
               this.showModal = false;
               this.loadData();
           },
           error: err => alert(err.error?.message || 'خطأ في إنشاء التحويل')
       });
    }
  }

  receive(id: number) {
      if(confirm('هل أنت متأكد من استلام التحويل وإضافة الكمية للمخزن الخاص بالفرع المستقبل؟')) {
          this.adminApi.receiveTransfer(id).subscribe({
              next: (res: any) => { alert(res.message); this.loadData(); },
              error: err => alert(err.error?.message || 'تعذر الاستلام')
          });
      }
  }

  cancel(id: number) {
      if(confirm('هل تريد إلغاء هذا التحويل ورد الكمية للمخزن المصدِّر؟')) {
          this.adminApi.cancelTransfer(id).subscribe({
              next: (res: any) => { alert(res.message); this.loadData(); },
              error: err => alert(err.error?.message || 'تعذر الإلغاء')
          });
      }
  }
}
