import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { Router } from '@angular/router';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
  standalone: true,
  imports: [CommonModule, FormsModule, MatCardModule, MatFormFieldModule, MatInputModule, MatButtonModule]
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

