import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../admin.service';
import { Router, RouterModule } from '@angular/router';

@Component({
  selector: 'app-users-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './users.component.html',
  styleUrls: ['./users.component.scss']
})
export class UsersAdminComponent implements OnInit {
  users: any[] = [];
  roles: any[] = [];
  currentUser: any = this.emptyUser();
  editingId: number | null = null;
  showModal = false;

  constructor(private adminApi: AdminService, public router: Router) {}

  ngOnInit() {
    this.adminApi.getRoles().subscribe({
      next: (res) => {
        const unwrapped = (res as any).data || res;
        this.roles = Array.isArray(unwrapped) ? unwrapped : (unwrapped.data || []);
      },
      error: () => this.roles = []
    });
    this.load();
  }

  emptyUser() {
    return { name: '', email: '', password: '', phone: '', role_name: '', is_active: true };
  }

  load() {
    this.adminApi.getUsers().subscribe({
      next: (res) => {
        const unwrapped = (res as any).data || res;
        this.users = Array.isArray(unwrapped) ? unwrapped : (unwrapped.data || []);
      },
      error: () => this.users = []
    });
  }

  openAddModal() {
    this.editingId = null;
    this.currentUser = this.emptyUser();
    this.showModal = true;
  }

  saveUser() {
    if (!this.currentUser.role_name) return alert('برجاء اختيار وظيفة/صلاحية للمستخدم');

    const ob = this.editingId 
       ? this.adminApi.updateUser(this.editingId, this.currentUser)
       : this.adminApi.createUser(this.currentUser);

    ob.subscribe({
       next: () => { 
           this.load(); 
           this.showModal = false;
           this.resetForm(); 
       },
       error: err => alert(err.error?.message || err.error?.error || 'خطأ في الحفظ')
    });
  }

  edit(u: any) {
    this.editingId = u.id;
    this.currentUser = { ...u, password: '', role_name: u.roles && u.roles.length > 0 ? u.roles[0].name : '' };
    this.showModal = true;
  }

  deleteUser(id: number) {
    if (confirm('تأكيد إيقاف حساب المستخدم؟ لن يتمكن من الدخول نهائياً.')) {
      this.adminApi.deleteUser(id).subscribe({
         next: () => this.load(),
         error: () => alert('خطأ في العملية')
      });
    }
  }

  resetForm() {
    this.editingId = null;
    this.currentUser = this.emptyUser();
  }
}

