import { redirect } from 'next/navigation';
import { DEFAULT_CHAT_ROUTE } from '../routes';

export default function HomePage() {
	redirect(DEFAULT_CHAT_ROUTE);
}
