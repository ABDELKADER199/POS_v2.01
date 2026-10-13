import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../admin.service';
import { Router, RouterModule } from '@angular/router';

@Component({
  selector: 'app-products-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './products.component.html',
  styleUrls: ['./products.component.scss']
})
export class ProductsAdminComponent implements OnInit {
  products: any[] = [];
  categories: any[] = [];
  currentProd: any = this.emptyProd();
  editingId: number | null = null;
  searchQuery = '';
  
  showModal = false;

  constructor(
    private adminApi: AdminService, 
    public router: Router
  ) {}

  ngOnInit() { 
    this.adminApi.getCategories().subscribe(res => this.categories = res);
    this.load(); 
  }

  emptyProd() {
    return { 
      product_code: '', 
      product_name: '', 
      category_id: null, 
      barcode: '', 
      buy_price: 0, 
      sell_price: 0, 
      min_quantity: 10, 
      is_active: true,
      unit: 'قطعة',
      tax_percent: 0
    };
  }

  load() {
    this.adminApi.getProducts(1, this.searchQuery).subscribe({
      next: (res) => {
        const unwrapped = res.data || res;
        this.products = unwrapped.data || unwrapped || [];
      },
      error: () => this.products = []
    });
  }

  openAddModal() {
    this.editingId = null;
    this.currentProd = this.emptyProd();
    this.showModal = true;
  }

  closeModal() {
    this.showModal = false;
    this.editingId = null;
  }

  saveProduct() {
    const ob = this.editingId 
       ? this.adminApi.updateProduct(this.editingId, this.currentProd)
       : this.adminApi.createProduct(this.currentProd);

    ob.subscribe({
       next: () => { 
         this.load(); 
         this.closeModal(); 
       },
       error: err => alert(err.error?.message || err.error?.error || 'حدث خطأ أثناء الحفظ. تأكد من صحة البيانات.')
    });
  }

  edit(p: any) {
    this.editingId = p.id;
    this.currentProd = { ...p };
    this.showModal = true;
  }

  delete(id: number) {
    if(confirm('سيتم حذف هذا المنتج بشكل نهائي.. هل أنت متأكد؟')) {
      this.adminApi.deleteProduct(id).subscribe({
         next: () => this.load(),
         error: err => alert(err.error?.error || 'حدث خطأ أثناء الحذف')
      });
    }
  }

  logout() {
    localStorage.clear();
    sessionStorage.clear();
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i];
        const eqPos = cookie.indexOf("=");
        const name = eqPos > -1 ? cookie.substr(0, eqPos) : cookie;
        document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 GMT";
    }
    this.router.navigate(['/login']);
  }
}
