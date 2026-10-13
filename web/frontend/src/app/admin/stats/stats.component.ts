import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../admin.service';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-stats-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './stats.component.html',
  styleUrls: ['./stats.component.scss']
})
export class StatsAdminComponent implements OnInit {
  stores: any[] = [];
  storeFilter = '';
  dateFrom = '';
  dateTo = '';
  
  metrics: any = {};
  dailyChart: any[] = [];
  hourlyChart: any[] = [];
  paymentChart: any[] = [];
  storeSales: any[] = [];
  topProducts: any[] = [];
  topCustomers: any[] = [];
  mostReturned: any[] = [];
  supplierStats: any[] = [];

  maxDailyValue = 1;
  maxHourlyValue = 1;
  paymentTotal = 1;

  constructor(private adminApi: AdminService) {
    const today = new Date();
    this.dateFrom = today.toISOString().split('T')[0];
    this.dateTo = today.toISOString().split('T')[0];
  }

  ngOnInit() {
    this.adminApi.getStatsStores().subscribe(res => {
      const unwrapped = (res as any).data || res;
      this.stores = Array.isArray(unwrapped) ? unwrapped : [];
    });
    this.loadDashboard();
  }

  loadDashboard() {
    this.adminApi.getDashboard(this.dateFrom, this.dateTo, this.storeFilter).subscribe(res => {
      const d = (res as any).data || res;
      this.metrics = d.metrics || {};
      this.dailyChart = d.daily_chart || [];
      this.hourlyChart = d.hourly_chart || [];
      this.paymentChart = d.payment_chart || [];
      this.storeSales = d.store_sales || [];
      this.topProducts = d.top_products || [];
      this.topCustomers = d.top_customers || [];
      this.mostReturned = d.most_returned || [];
      this.supplierStats = d.supplier_stats || [];

      this.maxDailyValue = Math.max(...this.dailyChart.map((d: any) => d.total || 0), 1);
      this.maxHourlyValue = Math.max(...this.hourlyChart.map((d: any) => d.total || 0), 1);
      this.paymentTotal = this.paymentChart.reduce((s: number, p: any) => s + (p.total || 0), 0) || 1;
    });
  }

  setPreset(preset: string) {
    const today = new Date();
    this.dateTo = today.toISOString().split('T')[0];
    if (preset === 'today') {
      this.dateFrom = this.dateTo;
    } else if (preset === 'week') {
      const d = new Date(today);
      d.setDate(d.getDate() - 6);
      this.dateFrom = d.toISOString().split('T')[0];
    } else if (preset === 'month') {
      this.dateFrom = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
    }
    this.loadDashboard();
  }

  barHeight(value: number, max: number): string {
    return Math.max((value / max) * 100, 2) + '%';
  }
}
