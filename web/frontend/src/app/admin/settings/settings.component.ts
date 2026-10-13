import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../admin.service';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-settings-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './settings.component.html',
  styleUrls: ['./settings.component.scss']
})
export class SettingsAdminComponent implements OnInit {
  settings: any = {
    store_name: '',
    store_phone: '',
    store_address: '',
    tax_number: '',
    receipt_footer: ''
  };
  
  saving = false;

  constructor(private adminApi: AdminService) {}

  ngOnInit() {
    this.adminApi.getSettings().subscribe(res => {
      const data = (res as any).data || res;
      if (data && typeof data === 'object') {
        this.settings = { ...this.settings, ...data };
      }
    });
  }

  save() {
    this.saving = true;
    this.adminApi.updateSettings(this.settings).subscribe({
      next: () => {
        this.saving = false;
        alert('تم حفظ الإعدادات بنجاح ✅');
      },
      error: (err) => {
        this.saving = false;
        alert(err.error?.message || 'حدث خطأ أثناء الحفظ');
      }
    });
  }
}
