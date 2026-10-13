import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../admin.service';
import { Router, RouterModule } from '@angular/router';

@Component({
  selector: 'app-categories-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './categories.component.html',
  styleUrls: ['./categories.component.scss']
})
export class CategoriesAdminComponent implements OnInit {
  categories: any[] = [];
  currentCat: any = { category_name: '', description: '', is_active: true };
  editingId: number | null = null;
  showModal = false;

  constructor(private adminApi: AdminService, public router: Router) {}

  ngOnInit() { this.load(); }

  load() {
    this.adminApi.getCategories().subscribe({
      next: (res) => {
        const unwrapped = (res as any).data || res;
        this.categories = Array.isArray(unwrapped) ? unwrapped : (unwrapped.data || []);
      },
      error: () => this.categories = []
    });
  }

  saveCategory() {
    const ob = this.editingId 
       ? this.adminApi.updateCategory(this.editingId, this.currentCat)
       : this.adminApi.createCategory(this.currentCat);

    ob.subscribe({
       next: () => { this.load(); this.showModal = false; this.resetForm(); },
       error: err => alert(err.error?.message || 'حدث خطأ أثناء الحفظ')
    });
  }

  edit(cat: any) {
    this.editingId = cat.id;
    this.currentCat = { ...cat };
    this.showModal = true;
  }

  delete(id: number) {
    if(confirm('سيتم حذف هذا القسم.. هل أنت متأكد؟')) {
      this.adminApi.deleteCategory(id).subscribe({
         next: () => this.load(),
         error: err => alert(err.error?.error || 'حدث خطأ أثناء الحذف')
      });
    }
  }

  resetForm() {
    this.editingId = null;
    this.currentCat = { category_name: '', description: '', is_active: true };
  }
}
