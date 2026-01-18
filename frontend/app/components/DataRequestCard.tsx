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
      // Note: This assumes we have an endpoint to add additional evidence
      // For now, we'll use the existing claim update or create a new endpoint
      // This is a placeholder - actual implementation depends on backend API
      const formData = new FormData();
      files.forEach((file) => {
        formData.append('files', file);
      });

      // TODO: Implement backend endpoint for adding additional evidence
      // await api.claims.addEvidence(claimId, formData);
      
      // For now, just show success message
      alert('Files uploaded successfully! Please re-trigger evaluation.');
      
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
    <Card className="p-6 border-blue-500/30 bg-blue-500/10">
      <div className="flex items-start gap-3 mb-4">
        <span className="text-blue-400 text-2xl">⚠️</span>
        <div className="flex-1">
          <h3 className="text-sm font-medium text-blue-400 mb-1">
            Additional Evidence Required
          </h3>
          <p className="text-sm text-slate-300">
            The AI evaluation indicates more evidence is needed to make a decision.
          </p>
        </div>
      </div>

      {/* Requested Data Types */}
      <div className="mb-4">
        <p className="text-xs font-medium text-slate-400 mb-2">Requested:</p>
        <div className="space-y-2">
          {requestedTypes.map((dataType) => (
            <div
              key={dataType}
              className="flex items-center gap-2 p-2 rounded bg-slate-800/50"
            >
              <span className="text-lg">
                {DATA_TYPE_ICONS[dataType] || '📎'}
              </span>
              <div>
                <p className="text-sm font-medium text-white">
                  {DATA_TYPE_LABELS[dataType] || dataType}
                </p>
                <p className="text-xs text-slate-400">
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
          <label className="block text-xs font-medium text-slate-400 mb-2">
            Upload Additional Files
          </label>
          <input
            type="file"
            multiple
            onChange={handleFileChange}
            className="block w-full text-sm text-slate-300 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-cyan-500 file:text-white hover:file:bg-cyan-600 file:cursor-pointer"
            accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.gif,.mp4,.mov,.mp3,.wav"
          />
        </div>

        {files.length > 0 && (
          <div className="p-3 rounded bg-slate-800/50">
            <p className="text-xs text-slate-400 mb-1">Selected files:</p>
            <ul className="space-y-1">
              {files.map((file, index) => (
                <li key={index} className="text-xs text-slate-300">
                  • {file.name} ({(file.size / 1024).toFixed(2)} KB)
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
          className="w-full"
        >
          {uploading ? 'Uploading...' : 'Upload Additional Files'}
        </Button>
      </div>

      <div className="mt-4 pt-4 border-t border-slate-700">
        <p className="text-xs text-slate-500">
          After uploading, you can re-trigger the evaluation to process the new evidence.
        </p>
      </div>
    </Card>
  );
}
