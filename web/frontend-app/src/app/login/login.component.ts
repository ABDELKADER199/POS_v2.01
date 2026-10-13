import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html'
})
export class LoginComponent{
  model = { email: '', password: '' };
  loading = false;
  error: string | null = null;
  constructor(private auth: AuthService, private router: Router) {}

  submit(){
    this.loading = true; this.error = null;
    this.auth.login(this.model).subscribe({
      next: ()=> this.router.navigate(['/cashier']),
      error: e=> { this.error = e?.error?.message || 'خطأ في المصادقة'; this.loading=false }
    })
  }
}
