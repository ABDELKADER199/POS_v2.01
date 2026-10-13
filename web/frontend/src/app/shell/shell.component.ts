import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../auth.service';

interface NavItem {
  path: string;
  label: string;
  icon: string;
  permission?: string;
}

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './shell.component.html',
  styleUrls: ['./shell.component.scss'],
})
export class ShellComponent implements OnInit {
  user: any = null;
  features: string[] = [];
  sidebarOpen = true;

  navItems: NavItem[] = [
    { path: '/cashier', label: 'الكاشير', icon: '💻', permission: 'sell.products' },
    { path: '/drawer', label: 'درج الكاشير', icon: '💵', permission: 'drawer.open' },
    { path: '/returns', label: 'مرتجعات', icon: '🔄', permission: 'returns.access' },
    { path: '/admin/products', label: 'المنتجات', icon: '📦', permission: 'products.edit' },
    { path: '/admin/categories', label: 'الفئات', icon: '🏷️', permission: 'products.edit' },
    { path: '/admin/inventory', label: 'المخزون', icon: '📋', permission: 'inventory.adjust' },
    { path: '/admin/purchases', label: 'المشتريات', icon: '🚛', permission: 'accounts.full_access' },
    { path: '/admin/users', label: 'المستخدمون', icon: '🛡️', permission: 'admin.manage_users' },
  ];

  constructor(private auth: AuthService, private router: Router) {}

  ngOnInit(): void {
    this.auth.loadUser().subscribe({
      next: (u) => {
        this.user = u?.data ?? u;
        this.auth.loadPermissions().subscribe();
        this.auth.loadFeatures().subscribe((f) => (this.features = f));
      },
      error: () => this.router.navigate(['/login']),
    });
  }

  visibleNav(): NavItem[] {
    return this.navItems.filter((item) => !item.permission || this.auth.hasPermission(item.permission));
  }

  logout(): void {
    this.auth.logout().subscribe();
  }

  toggleSidebar(): void {
    this.sidebarOpen = !this.sidebarOpen;
  }
}
