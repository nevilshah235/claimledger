'use client';

import { useState, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Textarea } from './ui';
import { api } from '@/lib/api';

interface ClaimFormProps {
  walletAddress?: string;
  onClaimCreated: (claimId: string) => void;
}

export function ClaimForm({ walletAddress, onClaimCreated }: ClaimFormProps) {
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      setFiles(prev => [...prev, ...newFiles]);
    }
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Wallet address is automatically used from authenticated user

    if (!amount || parseFloat(amount) <= 0) {
      setError('Please enter a valid claim amount');
      return;
    }

    setLoading(true);

    try {
      // Show files as being uploaded (they're already visible in the UI)
      const result = await api.claims.create({
        claim_amount: parseFloat(amount),
        description,
        files: files.length > 0 ? files : undefined,
      });

      // Only reset form on success
      onClaimCreated(result.claim_id);
      
      // Reset form
      setAmount('');
      setDescription('');
      setFiles([]);
    } catch (err) {
      // Don't clear files on error - user can see what they tried to upload
      setError(err instanceof Error ? err.message : 'Failed to submit claim. Files may not have been uploaded.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Submit New Claim</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Claim Amount */}
          <Input
            label="Claim Amount"
            type="number"
            step="0.01"
            min="0"
            placeholder="0.00"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            rightIcon={<span className="text-sm text-slate-400">USDC</span>}
          />

          {/* Description */}
          <Textarea
            label="Description"
            placeholder="Describe your claim (e.g., Car accident damage, medical expenses...)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
          />

          {/* File Upload */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Evidence Files
            </label>
            <div className="space-y-3">
              {/* Upload Button */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="w-full p-4 border-2 border-dashed border-slate-600 rounded-xl hover:border-cyan-500/50 hover:bg-white/5 transition-all cursor-pointer"
              >
                <div className="flex flex-col items-center gap-2">
                  <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  <span className="text-sm text-slate-400">
                    Click to upload files (images, documents)
                  </span>
                </div>
              </button>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="image/*,.pdf,.doc,.docx"
                onChange={handleFileChange}
                className="hidden"
                data-testid="file-input"
              />

              {/* File List */}
              {files.length > 0 && (
                <div className="space-y-2">
                  {files.map((file, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/10"
                    >
                      <div className="flex items-center gap-3">
                        {file.type.startsWith('image/') ? (
                          <svg className="w-5 h-5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                        ) : (
                          <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                        )}
                        <div>
                          <p className="text-sm text-white">{file.name}</p>
                          <p className="text-xs text-slate-400">
                            {(file.size / 1024).toFixed(1)} KB
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeFile(index)}
                        className="p-1 rounded hover:bg-white/10 transition-colors"
                      >
                        <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          {/* Submit Button */}
          <Button
            type="submit"
            className="w-full"
            size="lg"
            loading={loading}
            disabled={!walletAddress}
          >
            {!walletAddress ? 'Connect Wallet to Submit' : 'Submit Claim'}
          </Button>

          {/* Info */}
          <p className="text-xs text-slate-400 text-center">
            Evaluation cost: ~$0.35 USDC (x402 micropayments)
          </p>
        </form>
      </CardContent>
    </Card>
  );
}

export default ClaimForm;
