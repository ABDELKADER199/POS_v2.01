<?php
// مقتطفات لملف routes/api.php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;
use App\Http\Controllers\AuthController;

Route::post('/login', [AuthController::class, 'login']);
Route::post('/logout', [AuthController::class, 'logout'])->middleware('auth:sanctum');
Route::get('/me', [AuthController::class, 'me'])->middleware('auth:sanctum');
Route::get('/permissions', [AuthController::class, 'permissions'])->middleware('auth:sanctum');

// مثال Controller بسيط (App/Http/Controllers/AuthController.php)
/*
public function login(Request $req){
    $credentials = $req->only(['email','password']);
    if (!Auth::attempt($credentials)){
        return response()->json(['message'=>'Invalid credentials'], 401);
    }
    $user = Auth::user();
    $token = $user->createToken('api-token')->plainTextToken;
    return response()->json(['token'=>$token,'user'=>$user]);
}
*/
