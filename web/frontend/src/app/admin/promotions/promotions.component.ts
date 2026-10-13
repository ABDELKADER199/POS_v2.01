import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../admin.service';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-promotions-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './promotions.component.html',
  styleUrls: ['./promotions.component.scss']
})
export class PromotionsAdminComponent implements OnInit {
  promotions: any[] = [];
  filteredPromotions: any[] = [];
  categories: any[] = [];
  
  searchQuery = '';
  statusFilter = 'All';

  showModal = false;
  isEdit = false;
  
  promoForm: any = {};
  targetProducts: any[] = [];

  constructor(private adminApi: AdminService) {}

  ngOnInit() {
    this.adminApi.getCategories().subscribe(res => {
        const unwrapped = (res as any).data || res;
        this.categories = Array.isArray(unwrapped) ? unwrapped : (unwrapped.data || []);
    });
    this.loadData();
  }

  loadData() {
    this.adminApi.getPromotions().subscribe(res => {
        const unwrapped = (res as any).data || res;
        this.promotions = Array.isArray(unwrapped) ? unwrapped : (unwrapped.data || []);
        this.applyFilters();
    });
  }

  applyFilters() {
      this.filteredPromotions = this.promotions.filter(p => {
         const matchSearch = (p.name || '').includes(this.searchQuery) || (p.apply_to_name || '').includes(this.searchQuery);
         
         const today = new Date().getTime();
         const start = new Date(p.start_date).getTime();
         const end = new Date(p.end_date).getTime();
         let status = 'Inactive';
         if (!p.is_active) status = 'Inactive';
         else if (today >= start && today <= end) status = 'Active';
         else status = 'Expired';

         const matchStatus = this.statusFilter === 'All' || status === this.statusFilter;

         return matchSearch && matchStatus;
      });
  }

  getActiveCount(): number {
      return this.promotions.filter(p => {
          if (!p.is_active) return false;
          const today = new Date().getTime();
          const start = new Date(p.start_date).getTime();
          const end = new Date(p.end_date).getTime();
          return today >= start && today <= end;
      }).length;
  }

  getInactiveCount(): number {
      return this.promotions.length - this.getActiveCount();
  }

  getStatusClass(p: any) {
     if (!p.is_active) return 'badge-danger';
     const today = new Date().getTime();
     const start = new Date(p.start_date).getTime();
     const end = new Date(p.end_date).getTime();
     if (today >= start && today <= end) return 'badge-success';
     return 'badge-warning';
  }

  getStatusText(p: any) {
     if (!p.is_active) return 'متوقف';
     const today = new Date().getTime();
     const start = new Date(p.start_date).getTime();
     const end = new Date(p.end_date).getTime();
     if (today >= start && today <= end) return 'نشط الآن';
     return 'خارج الفترة';
  }

  openModal(promo?: any) {
     this.isEdit = !!promo;
     if (promo) {
         this.promoForm = { ...promo };
     } else {
         const today = new Date();
         const nextMonth = new Date();
         nextMonth.setMonth(nextMonth.getMonth() + 1);
         this.promoForm = {
             name: '',
             promo_type: 'percentage',
             value: 10,
             min_quantity: 1,
             buy_quantity: 1,
             apply_to: 'all',
             apply_to_id: null,
             start_date: today.toISOString().split('T')[0],
             end_date: nextMonth.toISOString().split('T')[0],
             funding_source: 'company',
             supplier_id: null,
             minimum_margin_percent: 5
         };
     }
     this.showModal = true;
  }

  searchPromoTarget(ev: any) {
      this.adminApi.searchPromotionProducts(ev.target.value).subscribe(res => {
         this.targetProducts = (res as any).data || res;
      });
  }

  savePromotion() {
      if(!this.promoForm.name || !this.promoForm.value) return alert('برجاء إدخال اسم العرض والقيمة');
      
      const ob = this.isEdit 
          ? this.adminApi.updatePromotion(this.promoForm.id, this.promoForm)
          : this.adminApi.createPromotion(this.promoForm);

      ob.subscribe({
          next: () => {
              this.showModal = false;
              this.loadData();
          },
          error: err => alert(err.error?.message || 'خطأ أثناء الحفظ')
      });
  }

  toggleActive(id: number) {
      this.adminApi.togglePromotion(id).subscribe(() => this.loadData());
  }

  delete(id: number) {
      if(confirm('هل أنت متأكد من حذف هذا العرض نهائياً؟')) {
          this.adminApi.deletePromotion(id).subscribe(() => this.loadData());
      }
  }
}
