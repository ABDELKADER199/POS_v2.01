import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, ElementRef, HostListener, OnInit, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { AuthService } from '../auth.service';
import { CashierService, Product } from './cashier.service';

@Component({
  selector: 'app-cashier',
  templateUrl: './cashier.component.html',
  styleUrls: ['./cashier.component.scss'],
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule]
})
export class CashierComponent implements OnInit {
  @ViewChild('searchInput') searchInput!: ElementRef;

  searchQuery: string = '';
  searchResults: Product[] = [];

  cart: any[] = [];
  cartTotals: { subtotal: number, tax: number, total: number } = { subtotal: 0, tax: 0, total: 0 };
  totals: any = { gross_total: 0, promo_discount: 0, manual_discount: 0, total: 0 };
  totalQty: number = 0;

  // Customer options
  customerName: string = '';
  customerPhone: string = '';
  customerAddress: string = '';

  // Payment
  discount: number = 0;
  paymentMethod: string = 'Cash';
  cashAmount: number = 0;
  cardAmount: number = 0;
  paidAmount: number = 0;
  change: number = 0;

  // Status message
  statusMessage: string = 'جاهز للبيع';
  statusKind: string = 'info'; // 'success', 'warning', 'danger', 'info'

  // Drawer
  drawerOpen: boolean = false;
  drawerDetails: any = null;

  // Held Invoices
  showHeldInvoices = false;
  heldInvoices: any[] = [];

  // Modals state
  showInquiryDialog = false;
  showOrdersDialog = false;
  showHistoryDialog = false;

  inquiryQuery: string = '';
  inquiryResult: any = null;

  isTaxInvoice = false;

  // Customer Display Channel
  displayChannel: BroadcastChannel | null = null;

  constructor(
    private auth: AuthService,
    private cashierApi: CashierService,
    private http: HttpClient
  ) {}

  ngOnInit() {
    this.checkDrawerStatus();
    this.setupDisplayChannel();
    // Focus search on init
    setTimeout(() => this.searchInput?.nativeElement.focus(), 100);
  }

  setupDisplayChannel() {
    try {
      this.displayChannel = new BroadcastChannel('pos_customer_display');
      this.displayChannel.postMessage({ type: 'welcome' });
    } catch (e) {
      console.warn('BroadcastChannel not supported or failed to init.');
    }
  }

  ngOnDestroy() {
    if (this.displayChannel) {
        this.displayChannel.close();
    }
  }

  // --- Keyboard Shortcuts ---
  @HostListener('window:keydown', ['$event'])
  handleKeyboardEvent(event: KeyboardEvent) {
    if (event.key === 'F12') {
      event.preventDefault();
      this.checkout(false);
    }
    if (event.ctrlKey && event.key === 'f') {
      event.preventDefault();
      this.searchInput?.nativeElement.focus();
    }
    if (event.ctrlKey && event.key === 's') {
      event.preventDefault();
      this.holdInvoice();
    }
  }

  setStatus(msg: string, kind: string = 'info') {
    this.statusMessage = msg;
    this.statusKind = kind;
    setTimeout(() => {
      if (this.statusMessage === msg) {
        this.statusMessage = 'جاهز للبيع';
        this.statusKind = 'info';
      }
    }, 6000);
  }

  toggleCustomerDisplay() {
    this.setStatus('جاري الفتح في شاشة أخرى...', 'success');
  }

  toggleTaxInvoice() {
    this.isTaxInvoice = !this.isTaxInvoice;
    this.setStatus(this.isTaxInvoice ? 'تم تفعيل الفاتورة الضريبية' : 'تم العودة للفاتورة العادية', 'info');
  }

  logout() {
    this.auth.logout().subscribe(() => {});
  }

  // --- Drawer Management ---
  checkDrawerStatus() {
    this.http.get<any>('/api/drawer/status').subscribe({
      next: (res) => {
        this.drawerOpen = res.is_open;
        this.drawerDetails = res;
      },
      error: () => { this.drawerOpen = false; }
    });
  }

  openDrawer() {
    const bal = prompt('ادخل رصيد البداية:');
    if (bal !== null) {
      this.http.post('/api/drawer/open', { store_id: 1, opening_balance: parseFloat(bal) || 0 })
        .subscribe(() => { this.checkDrawerStatus(); this.setStatus('تم فتح الدرج بنجاح', 'success'); });
    }
  }

  closeDrawer() {
    if (!this.drawerDetails?.drawer?.id && !this.drawerDetails?.id) return;
    const drawerId = this.drawerDetails?.drawer?.id ?? this.drawerDetails?.id;
    const cash = prompt('ادخل الكاش الفعلي:');
    const card = prompt('ادخل الفيزا الفعلية:');
    if (cash === null || card === null) return;

    this.http.post('/api/drawer/close', {
      drawer_id: drawerId,
      actual_cash: parseFloat(cash) || 0,
      actual_card: parseFloat(card) || 0,
    }).subscribe(() => {
      this.checkDrawerStatus();
      this.setStatus('تم غلق الدرج بنجاح', 'success');
    });
  }

  // --- Search & Add Product ---
  onSearchEnter() {
    const q = this.searchQuery.trim();
    if (!q) return;

    this.cashierApi.scanBarcode(q).subscribe({
      next: (res) => {
        // unwrapping ApiResponseMiddleware wrapper
        const unwrapped = res.data || res;
        // unwrapping direct { product: {...} } structure natively returned by the controller
        const p = unwrapped.product || unwrapped;

        if (p && p.id) {
          this.addSearchResult(p);
        } else {
          this.fallbackSearchByName(q);
        }
      },
      error: () => {
        this.fallbackSearchByName(q);
      }
    });
  }

  fallbackSearchByName(q: string) {
    this.cashierApi.getProducts(q).subscribe({
      next: (res) => {
        // unwrap ApiResponseMiddleware
        const unwrapped = res.data || res;
        // unwrap Laravel Pagination wrapper
        this.searchResults = unwrapped.data || unwrapped;

        if (Array.isArray(this.searchResults)) {
          if (this.searchResults.length === 1) {
            this.addSearchResult(this.searchResults[0]);
          } else if (this.searchResults.length === 0) {
            this.setStatus('لا يوجد منتج بهذا الاسم أو الباركود', 'danger');
          }
        }
      },
      error: () => {
        this.setStatus('خطأ في البحث', 'danger');
      }
    });
  }

  onInquiryEnter() {
    const q = this.inquiryQuery.trim();
    if (!q) return;

    this.cashierApi.scanBarcode(q).subscribe({
      next: (res) => {
        const unwrapped = res.data || res;
        this.inquiryResult = unwrapped.product || unwrapped;
      },
      error: () => {
        this.cashierApi.getProducts(q).subscribe({
          next: (res) => {
            const list = (res.data && res.data.data) ? res.data.data : (res.data || res);
            if (Array.isArray(list) && list.length > 0) {
              this.inquiryResult = list[0]; // Show first match for inquiry
            } else {
              this.inquiryResult = null;
              this.setStatus('لا يوجد منتج للاستعلام عنه', 'warning');
            }
          }
        });
      }
    });
  }

  addSearchResult(p: Product) {
    const exists = this.cart.find(i => i.id === p.id);
    if (exists) {
      exists.qty++;
    } else {
      this.cart.push({ ...p, qty: 1, unit_price: p.sell_price });
    }

    // Broadcast to Customer Display
    if (this.displayChannel) {
        this.displayChannel.postMessage({
            type: 'item_added',
            data: {
                name: p.product_name,
                price: p.sell_price,
                qty: exists ? exists.qty : 1,
                total: (exists ? exists.qty : 1) * p.sell_price
            }
        });
    }

    this.searchQuery = '';
    this.searchResults = [];
    this.calculateTotals();
  }

  updateQty(item: any, newQty: number) {
    const nextQty = Number(newQty) || 0;
    item.qty = nextQty;

    if (item.qty <= 0) {
      this.removeItem(item);
      return;
    }

    if (this.displayChannel) {
      this.displayChannel.postMessage({
        type: 'item_added',
        data: {
          name: item.product_name,
          price: item.unit_price,
          qty: item.qty,
          total: item.qty * item.unit_price
        }
      });
    }

    this.calculateTotals();
  }

  remove(item: any) {
    const target = typeof item === 'number' ? this.cart[item] : item;
    if (!target) return;
    this.removeItem(target);
  }

  removeItem(item: any) {
    this.cart = this.cart.filter(i => i !== item);
    this.updateTotals();
    this.calculateTotals();
  }

  calculateTotals() {
    this.cashierApi.calculateCart(this.cart).subscribe((res: any) => {
      this.totals = res?.data || res || { gross_total: 0, promo_discount: 0, manual_discount: 0, total: 0 };
      this.updateTotals();
      if (this.displayChannel) {
        this.displayChannel.postMessage({
          type: 'totals',
          data: {
            gross: this.totals.gross_total,
            discount: this.totals.promo_discount + this.totals.manual_discount,
            total: this.totals.total
          }
        });
      }
    });
  }

  clearCart() {
    this.cart = [];
    this.customerName = '';
    this.customerPhone = '';
    this.customerAddress = '';
    this.discount = 0;
    this.paidAmount = 0;
    this.cashAmount = 0;
    this.cardAmount = 0;
    this.paymentMethod = 'Cash';
    this.updateTotals();
    this.searchInput?.nativeElement.focus();
    if (this.displayChannel) this.displayChannel.postMessage({ type: 'welcome' });
  }

  updateTotals() {
    let sub = 0;
    for (let c of this.cart) {
      sub += ((c.sell_price || c.unit_price) * c.qty);
    }
    this.cartTotals.subtotal = sub;
    this.cartTotals.tax = 0; // Or integrate tax logic
    let t = sub - this.discount;
    this.cartTotals.total = t > 0 ? t : 0;
    this.totalQty = this.cart.reduce((s, i) => s + Number(i.qty), 0);
    this.onPaymentMethodChange();
  }

  onPaymentMethodChange() {
    const total = this.cartTotals.total;
    if (this.paymentMethod === 'Cash' || this.paymentMethod === 'Card') {
      this.paidAmount = total;
    } else if (this.paymentMethod === 'Credit') {
      this.paidAmount = 0;
    } else if (this.paymentMethod === 'Mixed') {
      this.cashAmount = total;
      this.cardAmount = 0;
      this.paidAmount = total;
    }
    this.onAmountChange();
  }

  onAmountChange() {
    const total = this.cartTotals.total;
    if (this.paymentMethod === 'Mixed') {
      const paid = Number(this.cashAmount) + Number(this.cardAmount);
      this.change = paid - total;
    } else {
      this.change = Number(this.paidAmount) - total;
    }
  }

  checkout(asPdf: boolean) {
    if (this.cart.length === 0) return;

    let payload = {
      items: this.cart.map(i => ({ id: i.id, qty: i.qty, unit_price: i.sell_price || i.unit_price, discount: 0 })),
      payment_method: this.paymentMethod,
      cash_amount: this.paymentMethod === 'Mixed' ? this.cashAmount : (this.paymentMethod === 'Cash' || this.paymentMethod === 'Credit' ? this.paidAmount : 0),
      card_amount: this.paymentMethod === 'Mixed' ? this.cardAmount : (this.paymentMethod === 'Card' ? this.paidAmount : 0),
      discount: this.discount,
      customer_name: this.customerName,
      customer_phone: this.customerPhone,
      customer_address: this.customerAddress,
      store_id: this.drawerDetails?.store_id || 1,
      is_tax_invoice: this.isTaxInvoice,
      as_pdf: asPdf
    };

    if (this.paymentMethod === 'Cash' && payload.cash_amount === 0) {
      payload.cash_amount = this.cartTotals.total;
    }

    this.cashierApi.checkout(payload).subscribe({
      next: (res) => {
        this.setStatus(`تم الدفع! رقم الفاتورة: #${res.invoice?.invoice_number || ''}`, 'success');
        this.clearCart();
      },
      error: (err) => {
        this.setStatus(err.error?.message || 'حدث خطأ أثناء الدفع', 'danger');
      }
    });
  }

  // --- Held Invoices ---
  loadHeldInvoices() {
    this.cashierApi.getHeldInvoices().subscribe(res => {
      const unwrapped = res.data || res;
      this.heldInvoices = unwrapped.data || unwrapped || [];
    });
  }

  holdInvoice() {
    if (this.cart.length === 0) return;
    const note = prompt('ملاحظة الفاتورة المعلقة:');
    const payload = {
      store_id: this.drawerDetails?.store_id || 1,
      notes: note || '',
      items: this.cart.map(i => ({ id: i.id, qty: i.qty, unit_price: i.sell_price || i.unit_price, discount: 0 }))
    };
    this.cashierApi.holdInvoice(payload).subscribe({
      next: () => {
        this.setStatus('تم تعليق الفاتورة بنجاح', 'success');
        this.clearCart();
      },
      error: () => this.setStatus('فشل تعليق الفاتورة', 'danger')
    });
  }

  restoreHeld(inv: any) {
    this.clearCart();
    if (inv.items) {
      inv.items.forEach((i: any) => {
        this.cart.push({
          id: i.product_id || i.id,
          product_name: i.product?.product_name || i.product_name || 'صنف غير معروف',
          sell_price: i.unit_price || i.price || 0,
          qty: i.quantity || i.qty || 1,
        });
      });
      this.updateTotals();
    }
    this.showHeldInvoices = false;
    this.deleteHeld(inv.id);
  }

  deleteHeld(id: number) {
    this.cashierApi.deleteHeldInvoice(id).subscribe(() => {
      this.loadHeldInvoices();
    });
  }
}
