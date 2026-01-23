'use client';

import { useState } from 'react';
import Image from 'next/image';
import { api } from '@/lib/api';
import { useAuth } from '../providers/AuthProvider';

type ChatMessage = { from: 'user' | 'assistant'; text: string };

export function ChatAssistant({
  claimId,
}: {
  claimId?: string | null;
}) {
  const { role } = useAuth();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      from: 'assistant',
      text: "Hi! I'm your UClaim assistant. How can I help with your claim today?",
    },
  ]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    setMessages((prev) => [...prev, { from: 'user', text: trimmed }]);
    setInput('');
    setSending(true);

    try {
      const res = await api.agent.chat({
        message: trimmed,
        role: role || undefined,
        claim_id: claimId || null,
      });
      setMessages((prev) => [...prev, { from: 'assistant', text: res.reply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          from: 'assistant',
          text:
            "I can't reach the assistant service right now. In demo mode, try: submit a claim → evaluation runs → upload requested evidence if needed → insurer settles approved claims.",
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      {/* Floating button */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-5 right-5 z-50 rounded-full w-24 h-24 shadow-lg overflow-hidden bg-transparent hover:scale-105 transition-transform p-0"
        aria-label="Open assistant"
      >
        <Image
          src="/chatbot-logo.png"
          alt="UClaim Assistant"
          width={96}
          height={96}
          className="w-full h-full object-cover"
          unoptimized
        />
      </button>

      {/* Panel */}
      {open && (
        <div className="fixed bottom-20 right-5 z-50 w-[360px] max-w-[calc(100vw-2.5rem)]">
          <div className="glass-card p-0 overflow-hidden bg-slate-900/95 backdrop-blur-xl border-slate-700/50">
            <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
              <div>
                <div className="coming-soon-badge">COMING SOON</div>
                <div className="text-xs text-slate-300 mt-1">
                  UClaim assistant - powered by advanced AI
                </div>
              </div>
              <button
                type="button"
                className="text-slate-300 hover:text-white"
                onClick={() => setOpen(false)}
              >
                ✕
              </button>
            </div>

            <div className="px-4 py-3 max-h-[360px] overflow-y-auto space-y-3">
              {messages.map((m, idx) => (
                <div
                  key={idx}
                  className={`text-sm rounded-xl px-3 py-2 border ${
                    m.from === 'assistant'
                      ? 'bg-white/10 border-white/20 text-slate-100'
                      : 'bg-cyan-500/20 border-cyan-500/30 text-white'
                  }`}
                >
                  {m.text}
                </div>
              ))}
            </div>

            <div className="px-4 py-3 border-t border-white/10 flex gap-2">
              <input
                className="flex-1 py-2 px-3 rounded-lg bg-slate-800/50 border border-slate-600/50 text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50"
                placeholder="Ask a question…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') send(input);
                }}
                disabled={sending}
              />
              <button
                type="button"
                className="btn-primary px-4 py-2 rounded-xl"
                onClick={() => send(input)}
                disabled={sending}
              >
                Send
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default ChatAssistant;
