import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../admin.service';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-inventory-count',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './inventory-count.component.html',
  styleUrls: ['./inventory-count.component.scss']
})
export class InventoryCountComponent implements OnInit {
  // Screens: 'list' | 'session'
  currentScreen = 'list';

  // List Screen Data
  sessions: any[] = [];
  stores: any[] = [];
  storeFilter = '';
  statusFilter = '';

  // Create Modal
  showCreateModal = false;
  newSession = {
    count_number: `INV-${new Date().getTime()}`,
    store_id: null,
    count_type: 'full',
    notes: ''
  };

  // Active Session Data
  activeSession: any = null;
  sessionItems: any[] = [];
  searchQuery = '';

  constructor(private adminApi: AdminService) {}

  ngOnInit() {
    this.loadStores();
    this.loadSessions();
  }

  loadStores() {
    this.adminApi.getCountStores().subscribe((res: any) => {
        this.stores = (res as any).data || res || [];
        if (this.stores.length > 0) this.newSession.store_id = this.stores[0].id;
    });
  }

  loadSessions() {
    this.adminApi.getCountSessions(this.statusFilter, this.storeFilter).subscribe((res: any) => {
        this.sessions = (res as any).data || res || [];
    });
  }

  openCreateModal() {
    this.newSession.count_number = `INV-${new Date().getTime()}`;
    this.showCreateModal = true;
  }

  createSession() {
    if (!this.newSession.store_id) return alert('برجاء اختيار الفرع');
    
    this.adminApi.createCountSession(this.newSession).subscribe({
        next: (res: any) => {
            alert('تم إنشاء جلسة الجرد بنجاح');
            this.showCreateModal = false;
            this.loadSessions();
            this.openSession({ id: res.session_id, count_number: this.newSession.count_number, status: 'open' });
        },
        error: (err: any) => alert(err.error?.error || 'حدث خطأ أثناء الإنشاء')
    });
  }

  openSession(session: any) {
    this.activeSession = session;
    this.currentScreen = 'session';
    this.searchQuery = '';
    this.loadSessionItems();
  }

  loadSessionItems() {
    if (!this.activeSession) return;
    this.adminApi.getCountSessionItems(this.activeSession.id, this.searchQuery).subscribe((res: any) => {
        const items = (res as any).data || res || [];
        this.sessionItems = items.map((i: any) => ({
            ...i,
            input_quantity: i.actual_quantity !== null ? i.actual_quantity : i.book_quantity
        }));
    });
  }

  searchItems(ev: any) {
    if (ev.key === 'Enter') {
        this.loadSessionItems();
    }
  }

  saveItemCount(item: any) {
    if (item.input_quantity === null || item.input_quantity === undefined) return;
    
    const payload = {
        actual_quantity: item.input_quantity,
        notes: item.notes
    };

    this.adminApi.updateCountItem(this.activeSession.id, item.id, payload).subscribe({
        next: (res: any) => {
            item.actual_quantity = item.input_quantity;
            item.variance = res.variance;
            
            // Re-select input text if we want to allow rapid scanning (optional behavior)
            // Can be enhanced by tracking input references
        },
        error: (err: any) => alert(err.error?.error || 'خطأ في الحفظ')
    });
  }

  approveSession() {
    if (!confirm('تنبيه: اعتماد الجلسة سيؤدي إلى تسوية أرصدة المخزون بالكميات الفعلية المدخلة وتسجيل فروقات الجرد مالياً. هل أنت متأكد؟')) return;

    this.adminApi.approveCountSession(this.activeSession.id).subscribe({
        next: (res: any) => {
            alert(res.message || 'تم الاعتماد بنجاح');
            this.backToList();
        },
        error: (err: any) => alert(err.error?.error || 'خطأ في الاعتماد')
    });
  }

  backToList() {
    this.currentScreen = 'list';
    this.activeSession = null;
    this.loadSessions();
  }
}
