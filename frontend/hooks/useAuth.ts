'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { loginUser, registerUser } from '../lib/authApi';
import { useAuthContext } from '../context/AuthContext';
import { HOME_ROUTE, LOGIN_ROUTE } from '../routes';
import { type LoginForm, type RegistrationForm } from '../types/user';

export function useAuth() {
  const router = useRouter();
  const { isAuthenticated, user, setSession, logOut } = useAuthContext();
  const [form, setForm] = useState<LoginForm>({ email: '', password: '' });
  const [error, setError] = useState('');
  const [isReady] = useState(true);

  useEffect(() => {
    if (isAuthenticated) router.replace(HOME_ROUTE);
  }, [isAuthenticated, router]);

  const updateField = (field: keyof LoginForm, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
    setError('');
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form.email.trim() || !form.password.trim()) {
      setError('Please enter both email and password.');
      return;
    }

    try {
      const response = await loginUser(form.email.trim(), form.password);
      setSession(response);
      router.push(HOME_ROUTE);
    } catch {
      setError('Sign in failed. Check your credentials and try again.');
    }
  };

  return { form, updateField, handleSubmit, error, isReady, currentUser: user, logOut: () => { logOut(); router.push(LOGIN_ROUTE); } };
}

export function useRegistration() {
  const router = useRouter();
  const { isAuthenticated, setSession } = useAuthContext();
  const [form, setForm] = useState<RegistrationForm>({ name: '', email: '', password: '', confirmPassword: '' });
  const [error, setError] = useState('');
  const [isReady] = useState(true);

  useEffect(() => {
    if (isAuthenticated) router.replace(HOME_ROUTE);
  }, [isAuthenticated, router]);

  const updateField = (field: keyof RegistrationForm, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
    setError('');
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (form.name.trim().length < 2) return setError('Please enter your name.');
    if (!form.email.trim() || !form.password) return setError('Please complete all fields.');
    if (form.password.length < 8) return setError('Password must be at least 8 characters.');
    if (form.password !== form.confirmPassword) return setError('Passwords do not match.');

    try {
      const response = await registerUser(form.name.trim(), form.email.trim(), form.password);
      setSession(response);
      router.push(HOME_ROUTE);
    } catch {
      setError('Registration failed. Make sure the FastAPI backend is running and try again.');
    }
  };

  return { form, updateField, handleSubmit, error, isReady };
}
