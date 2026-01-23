'use client';

import { useMemo, useState } from 'react';
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
      text:
        role === 'insurer'
          ? 'Ask me to summarize a claim, explain risk flags, or guide settlement.'
          : 'Ask me what evidence you need, explain status, or what to do next.',
    },
  ]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);

  const suggestions = useMemo(() => {
    if (role === 'insurer') {
      return [
        'Summarize this claim in plain English.',
        'What’s the recommended next action?',
        'Explain the decision and confidence.',
      ];
    }
    return [
      'What evidence do you need from me?',
      'Explain my claim status.',
      'What are my next steps?',
    ];
  }, [role]);

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
            'I can’t reach the assistant service right now. In demo mode, try: submit a claim → evaluation runs → upload requested evidence if needed → insurer settles approved claims.',
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
        className="fixed bottom-5 right-5 z-50 rounded-full w-12 h-12 gradient-hero shadow-lg flex items-center justify-center"
        aria-label="Open assistant"
      >
        <span className="text-white text-lg">AI</span>
      </button>

      {/* Panel */}
      {open && (
        <div className="fixed bottom-20 right-5 z-50 w-[360px] max-w-[calc(100vw-2.5rem)]">
          <div className="glass-card p-0 overflow-hidden">
            <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold text-white">Assistant</div>
                <div className="text-xs text-slate-400">
                  AI may be wrong; verify before paying out.
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
                      ? 'bg-white/5 border-white/10 text-slate-200'
                      : 'bg-cyan-500/10 border-cyan-500/20 text-white'
                  }`}
                >
                  {m.text}
                </div>
              ))}

              <div className="flex flex-wrap gap-2 pt-1">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    type="button"
                    className="text-xs px-2 py-1 rounded-full bg-white/5 border border-white/10 text-slate-200 hover:bg-white/10"
                    onClick={() => send(s)}
                    disabled={sending}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            <div className="px-4 py-3 border-t border-white/10 flex gap-2">
              <input
                className="input flex-1 py-2"
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

