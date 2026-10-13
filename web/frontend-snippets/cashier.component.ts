// مقتطف لصفحة الكاشير (CashierComponent)
import { Component } from '@angular/core';

@Component({
  selector: 'app-cashier',
  template: `
  <div class="cashier">
    <h2>نقطة البيع (Cashier)</h2>
    <div class="products">
      <!-- قائمة المنتجات -->
    </div>
    <div class="cart">
      <!-- السلة والملخص والدفع -->
    </div>
  </div>
  `
})
export class CashierComponent {
  cart = [] as any[];
  addProduct(p: any){ this.cart.push(p); }
  total(){ return this.cart.reduce((s, i)=> s + (i.price*i.qty), 0); }
}
