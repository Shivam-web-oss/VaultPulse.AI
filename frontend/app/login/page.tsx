import { LoginForm } from '../../components/auth/LoginForm';

export default function LoginPage() {
	return <main className="flex min-h-screen items-center justify-center bg-[#030b16] px-4 text-white"><div className="w-full max-w-md rounded-2xl border border-white/10 bg-[#101621]/90 p-6 shadow-[0_0_40px_rgba(69,111,255,0.15)]"><LoginForm /></div></main>;
}
