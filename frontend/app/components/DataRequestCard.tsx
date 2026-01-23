'use client';

import { useState } from 'react';
import { Card, Button } from './ui';
import { api } from '@/lib/api';

interface DataRequestCardProps {
  claimId: string;
  requestedData?: string[] | null;
  onFilesUploaded?: () => void;
}

const DATA_TYPE_LABELS: Record<string, string> = {
  document: 'Document',
  image: 'Image',
  video: 'Video',
  audio: 'Audio',
};

const DATA_TYPE_ICONS: Record<string, string> = {
  document: '📄',
  image: '🖼️',
  video: '🎥',
  audio: '🎵',
};

const DATA_TYPE_DESCRIPTIONS: Record<string, string> = {
  document: 'Invoice, receipt, or other supporting documents',
  image: 'Photos showing damage or evidence',
  video: 'Video evidence',
  audio: 'Audio recordings',
};

export function DataRequestCard({
  claimId,
  requestedData,
  onFilesUploaded,
}: DataRequestCardProps) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [files, setFiles] = useState<File[]>([]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setError('Please select at least one file');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      // Upload evidence and restart evaluation automatically
      await api.claims.addEvidence(claimId, files);
      await api.agent.evaluate(claimId);
      
      if (onFilesUploaded) {
        onFilesUploaded();
      }
      
      setFiles([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload files');
    } finally {
      setUploading(false);
    }
  };

  const requestedTypes = requestedData || ['document', 'image'];

  return (
    <Card className="p-6 admin-card border-blue-cobalt/30 bg-blue-cobalt/10">
      <div className="flex items-start gap-3 mb-4">
        <svg className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <div className="flex-1">
          <h3 className="text-sm font-semibold admin-text-primary mb-1">
            Additional Evidence Required
          </h3>
          <p className="text-sm admin-text-secondary mb-2">
            The AI evaluation indicates more evidence is needed to make a decision.
          </p>
          <div className="mt-3 p-3 rounded-lg bg-blue-cobalt/10 border border-blue-cobalt/20">
            <p className="text-xs admin-text-primary font-medium mb-1">What happens next:</p>
            <ol className="text-xs admin-text-secondary space-y-1 list-decimal list-inside">
              <li>Upload the requested evidence files below</li>
              <li>AI will automatically re-evaluate your claim with the new evidence</li>
              <li>If the evidence is sufficient, your claim will be processed automatically</li>
              <li>If more information is still needed, an insurer will review your claim manually</li>
            </ol>
          </div>
        </div>
      </div>

      {/* Requested Data Types */}
      <div className="mb-4">
        <p className="text-xs font-medium admin-text-secondary mb-2 uppercase tracking-wide">
          Evidence Types Requested:
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {requestedTypes.map((dataType) => (
            <div
              key={dataType}
              className="flex items-center gap-3 p-3 rounded-lg bg-white/5 border border-white/10 hover:border-blue-cobalt/30 transition-colors"
            >
              <span className="text-xl flex-shrink-0">
                {DATA_TYPE_ICONS[dataType] || '📎'}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium admin-text-primary">
                  {DATA_TYPE_LABELS[dataType] || dataType.charAt(0).toUpperCase() + dataType.slice(1)}
                </p>
                <p className="text-xs admin-text-secondary mt-0.5">
                  {DATA_TYPE_DESCRIPTIONS[dataType] || 'Additional evidence'}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* File Upload */}
      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium admin-text-secondary mb-2">
            Upload Additional Files
          </label>
          <div className="relative">
            <input
              type="file"
              multiple
              onChange={handleFileChange}
              className="block w-full text-sm admin-text-primary file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-cobalt file:text-white hover:file:bg-blue-cobalt-light file:cursor-pointer file:transition-colors"
              accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.gif,.mp4,.mov,.mp3,.wav"
            />
          </div>
          <p className="text-xs admin-text-secondary mt-1">
            Supported formats: PDF, Word, Images (JPG, PNG, GIF), Video (MP4, MOV), Audio (MP3, WAV)
          </p>
        </div>

        {files.length > 0 && (
          <div className="p-3 rounded-lg bg-white/5 border border-white/10">
            <p className="text-xs font-medium admin-text-secondary mb-2">Selected files ({files.length}):</p>
            <ul className="space-y-1.5">
              {files.map((file, index) => (
                <li key={index} className="flex items-center justify-between text-xs admin-text-primary">
                  <span className="flex items-center gap-2 flex-1 min-w-0">
                    <svg className="w-4 h-4 text-cyan-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span className="truncate">{file.name}</span>
                  </span>
                  <span className="admin-text-secondary ml-2 flex-shrink-0">
                    {(file.size / 1024).toFixed(1)} KB
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {error && (
          <div className="p-3 rounded bg-red-500/10 border border-red-500/30">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        <Button
          onClick={handleUpload}
          disabled={uploading || files.length === 0}
          className="w-full bg-blue-cobalt hover:bg-blue-cobalt-light text-white"
        >
          {uploading ? 'Uploading...' : 'Upload Additional Files'}
        </Button>
      </div>

      <div className="mt-4 pt-4 border-t border-white/10">
        <div className="flex items-start gap-2">
          <svg className="w-4 h-4 text-cyan-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-xs admin-text-secondary">
            <span className="font-medium text-cyan-400">Automatic re-evaluation:</span> After you upload files, the AI will automatically restart the evaluation process. You'll see a progress indicator and be notified when the evaluation is complete.
          </p>
        </div>
      </div>
    </Card>
  );
}
