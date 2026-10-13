import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-customer-display',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './customer-display.component.html',
  styleUrls: ['./customer-display.component.scss']
})
export class CustomerDisplayComponent implements OnInit, OnDestroy {
  channel: BroadcastChannel | null = null;
  idleTimer: any = null;

  mode = 'welcome'; // 'welcome' | 'item' | 'totals'
  
  // Item State
  productName = '';
  unitPrice = 0;
  quantity = 0;
  lineTotal = 0;

  // Totals State
  grossTotal = 0;
  discount = 0;
  finalTotal = 0;

  constructor(private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.channel = new BroadcastChannel('pos_customer_display');
    this.channel.onmessage = (event) => {
      this.handleMessage(event.data);
    };
    this.showWelcome();
  }

  ngOnDestroy() {
    if (this.channel) {
      this.channel.close();
    }
    if (this.idleTimer) {
      clearTimeout(this.idleTimer);
    }
  }

  handleMessage(msg: any) {
    if (!msg || !msg.type) return;

    if (this.idleTimer) {
      clearTimeout(this.idleTimer);
    }

    if (msg.type === 'welcome') {
      this.showWelcome();
    } 
    else if (msg.type === 'item_added') {
      this.mode = 'item';
      this.productName = msg.data.name;
      this.unitPrice = msg.data.price;
      this.quantity = msg.data.qty;
      this.lineTotal = msg.data.total;
      
      // Save totals internally just in case we timeout
      if (msg.totals) {
        this.saveTotals(msg.totals);
      }
      
      // Wait 3 seconds, if no more items scanned, show totals
      this.idleTimer = setTimeout(() => {
        this.showTotals();
      }, 3000);
      
    } 
    else if (msg.type === 'totals') {
      this.saveTotals(msg.data);
      this.showTotals();
    }
    
    this.cdr.detectChanges();
  }

  saveTotals(totals: any) {
    this.grossTotal = totals.gross || 0;
    this.discount = totals.discount || 0;
    this.finalTotal = totals.total || 0;
  }

  showWelcome() {
    this.mode = 'welcome';
    this.productName = '';
    this.grossTotal = 0;
    this.discount = 0;
    this.finalTotal = 0;
  }

  showTotals() {
    // Only show totals if we actually have items
    if (this.finalTotal > 0) {
      this.mode = 'totals';
    } else {
      this.showWelcome();
    }
    this.cdr.detectChanges();
  }
}
