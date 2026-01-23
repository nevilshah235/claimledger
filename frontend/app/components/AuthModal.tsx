'use client';

import { useState } from 'react';
import { Modal, Button, Input } from './ui';
import { api } from '@/lib/api';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (walletAddress: string, role: string) => void;
  role: 'claimant' | 'insurer';
}

/**
 * AuthModal Component
 * 
 * Handles user registration and login for claimants and insurers.
 * Automatically provisions Developer-Controlled wallets via backend.
 */
const ROLE_DISPLAY_NAMES: Record<'claimant' | 'insurer', string> = {
  claimant: 'Claimant',
  insurer: 'Administrator',
};

export function AuthModal({ isOpen, onClose, onSuccess, role }: AuthModalProps) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const roleDisplayName = ROLE_DISPLAY_NAMES[role];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (isLogin) {
        const response = await api.auth.login({ email, password });
        onSuccess(response.wallet_address || '', response.role);
      } else {
        const response = await api.auth.register({ email, password, role });
        onSuccess(response.wallet_address, response.role);
      }
      
      onClose();
      setEmail('');
      setPassword('');
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isLogin ? `Login as ${roleDisplayName}` : `Register as ${roleDisplayName}`}
      size="sm"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            Email
          </label>
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="your@email.com"
            required
            disabled={loading}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            Password
          </label>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
            disabled={loading}
            minLength={6}
          />
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => {
              setIsLogin(!isLogin);
              setError(null);
            }}
            className="text-sm text-primary hover:text-primary/80"
            disabled={loading}
          >
            {isLogin ? "Don't have an account? Register" : "Already have an account? Login"}
          </button>
        </div>

        <Button
          type="submit"
          variant="primary"
          className="w-full"
          disabled={loading}
        >
          {loading ? 'Processing...' : isLogin ? 'Login' : 'Register'}
        </Button>
      </form>
    </Modal>
  );
}
