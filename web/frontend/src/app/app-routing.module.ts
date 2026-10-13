import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from './auth.guard';
import { CashierComponent } from './cashier/cashier.component';
import { LoginComponent } from './login/login.component';
import { DrawerComponent } from './drawer/drawer.component';
import { ReturnsComponent } from './returns/returns.component';
import { CategoriesAdminComponent } from './admin/categories/categories.component';
import { ProductsAdminComponent } from './admin/products/products.component';
import { InventoryAdminComponent } from './admin/inventory/inventory.component';
import { InventoryCountComponent } from './admin/inventory-count/inventory-count.component';
import { PurchasesAdminComponent } from './admin/purchases/purchases.component';
import { UsersAdminComponent } from './admin/users/users.component';
import { AccountsAdminComponent } from './admin/accounts/accounts.component';
import { TransfersAdminComponent } from './admin/transfers/transfers.component';
import { CallCenterAdminComponent } from './admin/callcenter/callcenter.component';
import { PromotionsAdminComponent } from './admin/promotions/promotions.component';
import { StatsAdminComponent } from './admin/stats/stats.component';
import { SettingsAdminComponent } from './admin/settings/settings.component';
import { ShellComponent } from './shell/shell.component';
import { CustomerDisplayComponent } from './customer-display/customer-display.component';

const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'customer-display', component: CustomerDisplayComponent },
  {
    path: '',
    component: ShellComponent,
    canActivate: [AuthGuard],
    children: [
      { path: 'cashier', component: CashierComponent },
      { path: 'drawer', component: DrawerComponent },
      { path: 'returns', component: ReturnsComponent },
      { path: 'admin/categories', component: CategoriesAdminComponent },
      { path: 'admin/products', component: ProductsAdminComponent },
      { path: 'admin/inventory', component: InventoryAdminComponent },
      { path: 'admin/inventory-count', component: InventoryCountComponent },
      { path: 'admin/purchases', component: PurchasesAdminComponent },
      { path: 'admin/users', component: UsersAdminComponent },
      { path: 'admin/accounts', component: AccountsAdminComponent },
      { path: 'admin/transfers', component: TransfersAdminComponent },
      { path: 'admin/callcenter', component: CallCenterAdminComponent },
      { path: 'admin/promotions', component: PromotionsAdminComponent },
      { path: 'admin/stats', component: StatsAdminComponent },
      { path: 'admin/settings', component: SettingsAdminComponent },
      { path: '', redirectTo: 'cashier', pathMatch: 'full' },
    ],
  },
  { path: '**', redirectTo: 'cashier' },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {}
