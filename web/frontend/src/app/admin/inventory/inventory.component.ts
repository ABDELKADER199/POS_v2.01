import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../admin.service';
import { Router, RouterModule } from '@angular/router';

@Component({
  selector: 'app-inventory-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './inventory.component.html',
  styleUrls: ['./inventory.component.scss']
})
export class InventoryAdminComponent implements OnInit {
  products: any[] = [];
  searchQuery = '';

  constructor(private adminApi: AdminService, public router: Router) {}

  ngOnInit() { 
    this.load(); 
  }

  load() {
    this.adminApi.getInventory(1, this.searchQuery).subscribe({
      next: (res) => {
        const unwrapped = (res as any).data || res;
        const list = unwrapped.data || unwrapped;
        this.products = (Array.isArray(list) ? list : []).map((p: any) => ({
            ...p,
            new_quantity: p.quantity_in_stock,
            notes: ''
        }));
      },
      error: () => this.products = []
    });
  }

  adjust(p: any) {
    if (p.new_quantity === null || p.new_quantity === undefined) return alert('أدخل الكمية الجديدة');
    
    if (!confirm(`تأكيد تعديل رصيد ${p.product_name} من ${p.quantity_in_stock} إلى ${p.new_quantity}؟`)) return;

    const payload = {
        product_id: p.product_id,
        store_id: 1,
        new_quantity: p.new_quantity,
        notes: p.notes
    };

    this.adminApi.adjustInventory(payload).subscribe({
       next: (res) => { 
           alert(res.message || 'تم تعديل الرصيد بنجاح'); 
           p.quantity_in_stock = p.new_quantity;
       },
       error: err => alert(err.error?.error || 'حدث خطأ أثناء تعديل المخزون')
    });
  }
}

