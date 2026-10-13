import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DrawerService } from './drawer.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-drawer',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './drawer.component.html',
  styleUrls: ['./drawer.component.scss']
})
export class DrawerComponent implements OnInit {
  status: any = null;
  openingBalance: number = 0;
  closingBalance: number = 0;

  constructor(private drawerApi: DrawerService, private router: Router) {}

  ngOnInit() {
    this.checkStatus();
  }

  checkStatus() {
    this.drawerApi.getStatus().subscribe({
      next: (res: any) => {
        const unwrapped = res.data || res;
        this.status = unwrapped;
        if (unwrapped?.drawer?.expected_balance) {
           this.closingBalance = unwrapped.drawer.expected_balance;
        }
      },
      error: () => this.status = null
    });
  }

  openDrawer() {
    this.drawerApi.open(this.openingBalance).subscribe({
      next: () => this.checkStatus(),
      error: err => alert(err.error?.error || err.error?.message || "حدث خطأ أثناء فتح الدرج")
    });
  }

  closeDrawer() {
    if(!this.status?.drawer?.id) return;
    if(confirm('هل أنت متأكد من جرد هذه الوردية وإغلاقها نهائياً؟')) {
      this.drawerApi.close(this.status.drawer.id, this.closingBalance).subscribe({
        next: () => {
           alert("✅ تم إغلاق الدرج والوردية بنجاح.");
           this.router.navigate(['/login']);
        },
        error: err => alert(err.error?.error || err.error?.message || "حدث خطأ أثناء الإغلاق")
      });
    }
  }

  backToCashier() {
    this.router.navigate(['/cashier']);
  }
}

