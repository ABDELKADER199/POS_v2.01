import { Component, OnInit } from '@angular/core';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-cashier',
  templateUrl: './cashier.component.html'
})
export class CashierComponent implements OnInit{
  products = [
    { id:1, name: 'منتج A', price: 10 },
    { id:2, name: 'منتج B', price: 25 },
    { id:3, name: 'منتج C', price: 5 }
  ];
  cart: any[] = [];
  constructor(private auth: AuthService) {}
  ngOnInit(){ }
  add(p:any){
    const exists = this.cart.find(i=>i.id===p.id);
    if (exists) exists.qty++;
    else this.cart.push({ ...p, qty: 1 });
  }
  remove(item:any){ this.cart = this.cart.filter(i=>i!==item); }
  total(){ return this.cart.reduce((s,i)=> s + i.price*i.qty, 0); }
  checkout(){
    // تواصل مع API لإنشاء فاتورة (يتم تنفيذ endpoint لاحقاً)
    alert('دفع: ' + this.total());
    this.cart = [];
  }
  logout(){ this.auth.logout().subscribe(()=>{}); }
}
