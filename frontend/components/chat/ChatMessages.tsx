import type { Message as MessageType } from '../../types/chat';
import { Message } from './Message';

export function ChatMessages({ messages }: { messages: MessageType[] }) {
  return <div className="space-y-3">{messages.map((message) => <Message key={message.id} message={message} />)}</div>;
}
