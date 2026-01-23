'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { Button } from './ui';

interface EvidenceFile {
  id: string;
  file_type: string;
  file_path: string;
  file_size: number | null;
  mime_type: string | null;
  created_at: string;
}

interface EvidenceViewerProps {
  claimId: string;
}

export function EvidenceViewer({ claimId }: EvidenceViewerProps) {
  const [evidence, setEvidence] = useState<EvidenceFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewingFile, setViewingFile] = useState<string | null>(null);

  useEffect(() => {
    loadEvidence();
  }, [claimId]);

  const loadEvidence = async () => {
    try {
      setLoading(true);
      setError(null);
      const files = await api.claims.getEvidence(claimId);
      setEvidence(files);
    } catch (err: any) {
      setError(err.message || 'Failed to load evidence files');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (evidenceId: string, filename: string) => {
    try {
      const blob = await api.claims.downloadEvidence(claimId, evidenceId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      alert(`Failed to download file: ${err.message}`);
    }
  };

  const handleView = async (evidenceId: string, mimeType: string | null) => {
    try {
      const blob = await api.claims.downloadEvidence(claimId, evidenceId);
      const url = window.URL.createObjectURL(blob);
      setViewingFile(url);
    } catch (err: any) {
      alert(`Failed to view file: ${err.message}`);
    }
  };

  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return 'Unknown size';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (fileType: string, mimeType: string | null) => {
    if (fileType === 'image' || (mimeType && mimeType.startsWith('image/'))) {
      return (
        <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      );
    }
    return (
      <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    );
  };

  const getFileName = (filePath: string) => {
    return filePath.split('/').pop() || filePath;
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-2">
        <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm text-blue-300/70">Loading evidence files...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <div className="text-sm text-red-400 mb-2">{error}</div>
        <Button variant="secondary" size="sm" onClick={loadEvidence} className="text-xs">
          Retry
        </Button>
      </div>
    );
  }

  if (evidence.length === 0) {
    return (
      <div className="text-sm text-blue-300/50 italic">No evidence files uploaded yet.</div>
    );
  }

  return (
    <>
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-blue-300/70 font-medium">Evidence Files:</span>
            <span className="text-xs text-blue-400/50">({evidence.length})</span>
          </div>
          <Button variant="ghost" size="sm" onClick={loadEvidence} className="text-xs">
            Refresh
          </Button>
        </div>
          <div className="space-y-2">
            {evidence.map((file) => {
              const filename = getFileName(file.file_path);
              const isImage = file.file_type === 'image' || (file.mime_type && file.mime_type.startsWith('image/'));
              
              return (
                <div
                  key={file.id}
                  className="flex items-center justify-between p-3 rounded-lg border border-blue-500/20 bg-blue-500/10 hover:bg-blue-500/15 transition-colors"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    {getFileIcon(file.file_type, file.mime_type)}
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium admin-text-primary truncate">{filename}</p>
                      <p className="text-xs admin-text-secondary">
                        {file.file_type} • {formatFileSize(file.file_size)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {isImage && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleView(file.id, file.mime_type)}
                        className="text-xs"
                      >
                        View
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDownload(file.id, filename)}
                      className="text-xs"
                    >
                      Download
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
      </div>

      {/* Image viewer modal */}
      {viewingFile && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={() => {
            setViewingFile(null);
            window.URL.revokeObjectURL(viewingFile);
          }}
        >
          <div className="relative max-w-7xl max-h-[90vh] p-4">
            <button
              onClick={() => {
                setViewingFile(null);
                window.URL.revokeObjectURL(viewingFile);
              }}
              className="absolute top-6 right-6 text-white hover:text-gray-300 bg-black/50 rounded-full p-2 z-10"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            <img
              src={viewingFile}
              alt="Evidence"
              className="max-w-full max-h-[90vh] object-contain rounded-lg"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        </div>
      )}
    </>
  );
}
