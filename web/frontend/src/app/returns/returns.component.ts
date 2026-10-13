import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ReturnsService } from './returns.service';
import { Router, RouterModule } from '@angular/router';

@Component({
  selector: 'app-returns',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './returns.component.html',
  styleUrls: ['./returns.component.scss']
})
export class ReturnsComponent {
  invoiceNumber = '';
  invoiceDetails: any = null;
  returnReason = '';
  itemsToReturn: any[] = [];

  constructor(private returnApi: ReturnsService, private router: Router) {}

  search() {
    if (!this.invoiceNumber.trim()) return;
    this.returnApi.getInvoice(this.invoiceNumber).subscribe({
      next: (res: any) => {
          const unwrapped = res.data || res;
          this.invoiceDetails = unwrapped;
          if (unwrapped.items) {
             this.itemsToReturn = unwrapped.items.map((i:any) => ({ ...i, selected: false, return_qty: 0 }));
          } else {
             this.itemsToReturn = [];
          }
      },
      error: err => {
          alert(err.error?.error || err.error?.message || 'لم يتم العثور على الفاتورة. تأكد من الرقم.');
          this.invoiceDetails = null;
      }
    });
  }

  processReturn() {
    const selected = this.itemsToReturn.filter(i => i.selected && i.return_qty > 0 && i.return_qty <= i.available_to_return);
    
    if(selected.length === 0) return alert('يجب تحديد صنف واحد على الأقل وإدخال كمية صحيحة متاحة للرد.');
    
    const payload = {
       invoice_id: this.invoiceDetails.invoice.id,
       reason: this.returnReason,
       items: selected.map(i => ({ product_id: i.product_id, quantity: i.return_qty }))
    };

    if(confirm('سيتم خصم الكمية وإرجاع قيمتها من الخزينة. هل أنت متأكد من تنفيذ هذا المرتجع؟')) {
      this.returnApi.processReturn(payload).subscribe({
        next: (res: any) => {
            const unwrapped = res.data || res;
            alert(`✅ تم تنفيذ المرتجع بنجاح.\n\nالمبلغ المسترد نقداً للعميل: ${unwrapped.cash_refund || 0} ج.م\nالمديونية المُسواة (Credit): ${unwrapped.credit_adjustment || 0} ج.م`);
            this.invoiceDetails = null;
            this.invoiceNumber = '';
            this.itemsToReturn = [];
            this.returnReason = '';
        },
        error: err => alert(err.error?.error || err.error?.message || 'حدث خطأ أثناء تنفيذ المرتجع')
      });
    }
  }
}

