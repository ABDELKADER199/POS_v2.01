import { Injectable } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivate, Router } from '@angular/router';
import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class PermissionGuard implements CanActivate {
  constructor(private auth: AuthService, private router: Router) {}
  canActivate(route: ActivatedRouteSnapshot): boolean {
    const required = route.data['permission'] as string | undefined;
    const user = this.auth.getUser();
    if (!required || !user) return this.auth.isAuthenticated();
    const perms = user.permissions || user.roles || [];
    const ok = Array.isArray(perms) ? perms.includes(required) : false;
    if (!ok) this.router.navigate(['/']);
    return ok;
  }
}
