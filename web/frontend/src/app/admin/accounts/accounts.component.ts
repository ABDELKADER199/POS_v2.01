import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../admin.service';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-accounts-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './accounts.component.html',
  styleUrls: ['./accounts.component.scss']
})
export class AccountsAdminComponent implements OnInit {
  activeTab: string = 'overview';
  
  // Data
  summary: any = null;
  expenses: any[] = [];
  ledger: any[] = [];

  // Forms
  expenseForm = { amount: null, type: 'نثريات', description: '', is_personal: false };
  treasuryForm = { amount: null, type: 'In', description: '' };

  constructor(private adminApi: AdminService) {}

  ngOnInit() {
    this.loadData();
  }

  setTab(tab: string) {
    this.activeTab = tab;
  }

  loadData() {
    // 1. Load Summary
    this.adminApi.getAccountsSummary().subscribe(res => {
       this.summary = res.data || res;
    });

    // 2. Load Expenses
    this.adminApi.getExpenses().subscribe(res => {
       const unwrapped = res.data || res;
       this.expenses = Array.isArray(unwrapped) ? unwrapped : (unwrapped.data || []);
    });

    // 3. Load Ledger
    this.adminApi.getLedger().subscribe((res: any) => {
       const unwrapped = res.data || res;
       this.ledger = Array.isArray(unwrapped) ? unwrapped : (unwrapped.data || []);
    });
  }

  saveExpense() {
    if (!this.expenseForm.amount || !this.expenseForm.type) return alert('الرجاء إدخال المبلغ ونوع المصروف');
    
    if(confirm('تأكيد خصم المصروف من عهدة الخزينة؟')) {
      this.adminApi.storeExpense(this.expenseForm).subscribe({
        next: () => {
          alert('✅ تم تسجيل المصروف');
          this.expenseForm = { amount: null, type: 'نثريات', description: '', is_personal: false };
          this.loadData();
        },
        error: err => alert(err.error?.message || 'حدث خطأ')
      });
    }
  }

  saveTreasuryMovement() {
    if (!this.treasuryForm.amount || !this.treasuryForm.description) return alert('الرجاء إدخال المبلغ والسبب التفصيلي');
    
    const msg = this.treasuryForm.type === 'In' ? 'إيداع نقدية إلى الخزينة' : 'سحب/تصفية نقدية من الخزينة';
    if(confirm(`تأكيد عملية (${msg}) بقيمة ${this.treasuryForm.amount} ج.م؟`)) {
      this.adminApi.storeTreasuryAdjustment(this.treasuryForm).subscribe({
        next: () => {
          alert('✅ تم تنفيذ الحركة بنجاح');
          this.treasuryForm = { amount: null, type: 'In', description: '' };
          this.loadData();
        },
        error: err => alert(err.error?.message || 'حدث خطأ')
      });
    }
  }
}
