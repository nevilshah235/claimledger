'use client';

import { useState, useEffect } from 'react';
import { Card, Button } from './ui';
import { AgentResult } from '@/lib/types';
import { api } from '@/lib/api';

interface EvidenceFile {
  id: string;
  file_type: string;
  file_path: string;
  file_size: number | null;
  mime_type: string | null;
  created_at: string;
}

interface ExtractedInfoSummaryProps {
  agentResults: AgentResult[];
  /** When provided, fetches and displays the uploaded documents/images above the extracted summary. */
  claimId?: string;
}

// Field group labels and their sort order
const FIELD_GROUPS: Record<string, { label: string; order: number }> = {
  document: { label: 'Document & invoice', order: 1 },
  vehicle: { label: 'Vehicle', order: 2 },
  claim: { label: 'Claim & people', order: 3 },
  workshop: { label: 'Workshop & contact', order: 4 },
  financial: { label: 'Financial summary', order: 5 },
  other: { label: 'Other', order: 6 },
};

// Keywords (lowercase) to assign fields to groups
const GROUP_KEYWORDS: Record<string, string[]> = {
  document: ['vendor', 'invoice', 'vro', 'policy_number', 'claim_number', 'document_type', 'content_type', 'structure'],
  vehicle: ['vehicle', 'registration', 'engine', 'owner_name', 'make', 'model', 'vehicle_age'],
  claim: ['surveyor', 'coordinator', 'accident'],
  workshop: ['workshop', 'gst', 'toll', 'payment_to'],
  financial: ['liability', 'deductible', 'salvage', 'towing', 'customer_liability', 'digit_liability', 'non_standard', 'standard_amount', 'amount', 'total'],
};

function getFieldGroup(key: string): string {
  const k = key.toLowerCase();
  for (const [group, keywords] of Object.entries(GROUP_KEYWORDS)) {
    if (keywords.some((kw) => k.includes(kw) || k === kw)) return group;
  }
  return 'other';
}

function groupFields(fields: Record<string, any>): Record<string, Record<string, any>> {
  const grouped: Record<string, Record<string, any>> = {};
  for (const [key, value] of Object.entries(fields)) {
    const g = getFieldGroup(key);
    if (!grouped[g]) grouped[g] = {};
    grouped[g][key] = value;
  }
  return grouped;
}

// Sensitive field keys (PII, identifiers): excluded from UI display
function isSensitiveField(key: string): boolean {
  const k = key.toLowerCase();
  const patterns = [
    'owner_name', 'owner',
    'policy_number', 'policy_no', 'policyno',
    'claim_number', 'claim_no', 'claimno',
    'engine_number', 'engine_no', 'engineno',
    'chassis_number', 'chassis_no', 'chassino', 'chassis', 'chasis_number', 'chasis_no', 'chasis',
    'registration_number', 'registration_no', 'reg_no', 'vehicle_registration',
    'surveyor_name', 'surveyor',
    'claim_coordinator', 'coordinator',
    'workshop_gst_number', 'workshop_gst', 'gst_number', 'gst_no',
  ];
  return patterns.some((p) => k === p || k.includes(p));
}

// Helper function to format field names (convert snake_case to Title Case)
function formatFieldName(key: string): string {
  return key
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// Helper function to format field values (preserve currency symbols like ₹ from the value string)
function formatFieldValue(value: any): string {
  if (value === null || value === undefined) return 'N/A';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') {
    if (value % 1 !== 0 || value > 100) return `$${value.toFixed(2)}`;
    return value.toString();
  }
  if (Array.isArray(value)) return value.length > 0 ? value.join(', ') : 'None';
  if (typeof value === 'object') return JSON.stringify(value, null, 2);
  return String(value);
}

function getCurrencyPrefix(currency: unknown): string {
  if (currency == null || typeof currency !== 'string') return '$';
  const c = String(currency).trim().toUpperCase();
  if (/^(INR|RS\.?|₹|RUPEES?|INDIAN\s*RUPEES?)$/i.test(c)) return 'Rs. ';
  return '$';
}

function isMoneyColumn(header: string): boolean {
  const h = header.toLowerCase();
  return h === 'unit_price' || h === 'unit price' || h === 'total' || h === 'amount' || h === 'price' ||
    h.includes('price') || (h.includes('total') && !h.includes('quantity'));
}

function formatFieldValueForCell(value: any, header: string, currency: unknown): string {
  if (isMoneyColumn(header)) {
    const n = typeof value === 'number' ? value : (typeof value === 'string' && /^-?[\d.]+$/.test(value) ? Number(value) : NaN);
    if (!Number.isNaN(n)) return getCurrencyPrefix(currency) + Number(n).toFixed(2);
  }
  return formatFieldValue(value);
}

// Component to render a single field
function FieldDisplay({ label, value }: { label: string; value: any }) {
  if (value === null || value === undefined || value === '') return null;
  return (
    <div className="flex items-start gap-2">
      <span className="text-slate-400 shrink-0">{label}:</span>
      <span className="text-slate-100 break-words">{formatFieldValue(value)}</span>
    </div>
  );
}

// Section: grouped key-value fields with a two-column grid
function FieldGroupSection({
  title,
  fields,
  formatKey = formatFieldName,
}: {
  title: string;
  fields: Record<string, any>;
  formatKey?: (k: string) => string;
}) {
  const entries = Object.entries(fields).filter(
    ([k, v]) => v != null && v !== '' && !isSensitiveField(k)
  );
  if (entries.length === 0) return null;
  return (
    <div className="pb-3 border-b border-slate-600">
      <div className="text-xs font-semibold text-slate-200 mb-3 uppercase tracking-wide">{title}</div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
        {entries.map(([key, value]) => (
          <FieldDisplay key={key} label={formatKey(key)} value={value} />
        ))}
      </div>
    </div>
  );
}

// Line items as a table (always visible, with section header). Uses document currency for Unit Price, Total, etc.
function LineItemsTable({ lineItems, currency }: { lineItems: any[]; currency?: unknown }) {
  if (!lineItems || lineItems.length === 0) return null;

  const cols = new Set<string>();
  lineItems.forEach((item) => Object.keys(item || {}).forEach((k) => cols.add(k)));
  const prefer = ['item_name', 'description', 'quantity', 'unit_price', 'total', 'item', 'sku', 'category'];
  const headers = prefer.filter((h) => cols.has(h));
  Array.from(cols).filter((c) => !prefer.includes(c)).forEach((c) => headers.push(c));
  const filteredHeaders = headers.filter((h) => !isSensitiveField(h));
  if (filteredHeaders.length === 0) return null;

  return (
    <div className="pt-4 border-t border-slate-600">
      <div className="text-xs font-semibold text-slate-200 mb-3 uppercase tracking-wide">
        Line Items ({lineItems.length})
      </div>
      <div className="overflow-x-auto rounded-lg border border-slate-600">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-600 bg-slate-800/50">
              {filteredHeaders.map((h) => (
                <th key={h} className="text-left px-3 py-2 text-slate-300 font-medium">
                  {formatFieldName(h)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {lineItems.map((item, idx) => (
              <tr key={idx} className="border-b border-slate-700/50 last:border-0 hover:bg-slate-800/30">
                {filteredHeaders.map((h) => (
                  <td key={h} className="px-3 py-2 text-slate-100">
                    {formatFieldValueForCell((item || {})[h], h, currency)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Normalize table from extraction: headers as array, rows as array-of-arrays when possible
function normalizeTable(table: { headers?: unknown; rows?: unknown }): { headers: string[]; rows: (string | number)[][] } {
  let headers: string[] = [];
  if (Array.isArray(table.headers)) {
    headers = table.headers.map((h) => (h != null ? String(h).trim() : '')).filter(Boolean);
  } else if (typeof table.headers === 'string') {
    headers = table.headers.split(/[,;|]/).map((h) => h.trim()).filter(Boolean);
  }

  let rows: (string | number)[][] = [];
  if (Array.isArray(table.rows)) {
    rows = table.rows.map((row) => {
      if (Array.isArray(row)) {
        return row.map((c) => (c != null ? String(c) : ''));
      }
      if (row && typeof row === 'object' && !Array.isArray(row)) {
        return headers.map((h) => String((row as Record<string, unknown>)[h] ?? ''));
      }
      return [String(row)];
    });
  }
  return { headers, rows };
}

// Component to render tables (headers + full data grid when rows are available). Currency-aware for money columns.
function TablesDisplay({ tables, currency }: { tables: any[]; currency?: unknown }) {
  const [expanded, setExpanded] = useState(false);

  if (!tables || tables.length === 0) return null;

  return (
    <div className="pt-2 border-t border-slate-600">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-slate-300 hover:text-slate-100 text-xs mb-2"
      >
        <span>{expanded ? '▼' : '▶'}</span>
        <span>Tables ({tables.length})</span>
      </button>
      {expanded && (
        <div className="space-y-3 ml-4">
          {tables.map((table, idx) => {
            const { headers, rows } = normalizeTable(table);
            const keptIndices = headers.map((h, i) => (isSensitiveField(h) ? -1 : i)).filter((i) => i >= 0);
            const safeHeaders = keptIndices.map((i) => headers[i]);
            const canShowGrid = safeHeaders.length > 0 && rows.length > 0;

            return (
              <div key={idx} className="p-2 rounded bg-slate-800/50 text-xs">
                {table.summary && <FieldDisplay label="Summary" value={table.summary} />}
                {safeHeaders.length > 0 && (
                  <div className="mt-2">
                    {canShowGrid ? (
                      <div className="overflow-x-auto rounded-lg border border-slate-600">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="border-b border-slate-600 bg-slate-800/50">
                              {safeHeaders.map((h) => (
                                <th key={h} className="text-left px-2 py-1.5 text-slate-300 font-medium">
                                  {formatFieldName(h)}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {rows.map((row, rIdx) => (
                              <tr key={rIdx} className="border-b border-slate-700/50 last:border-0 hover:bg-slate-800/30">
                                {keptIndices.map((colIdx, cIdx) => (
                                  <td key={cIdx} className="px-2 py-1.5 text-slate-100">
                                    {formatFieldValueForCell(Array.isArray(row) ? row[colIdx] : '', safeHeaders[cIdx], currency)}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <>
                        <div className="text-slate-300 mb-1">Headers: {safeHeaders.join(', ')}</div>
                        {rows.length > 0 && <div className="text-slate-200">{rows.length} row(s)</div>}
                      </>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function getEvidenceFileName(filePath: string) {
  return filePath.split('/').pop() || filePath;
}

function formatEvidenceFileSize(bytes: number | null) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ExtractedInfoSummary({ agentResults, claimId }: ExtractedInfoSummaryProps) {
  const [evidence, setEvidence] = useState<EvidenceFile[]>([]);
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);
  const [viewingFile, setViewingFile] = useState<string | null>(null);

  useEffect(() => {
    if (!claimId) {
      setEvidence([]);
      setEvidenceError(null);
      return;
    }
    let cancelled = false;
    setEvidenceLoading(true);
    setEvidenceError(null);
    api.claims.getEvidence(claimId)
      .then((files) => {
        if (!cancelled) setEvidence(files);
      })
      .catch((err: unknown) => {
        if (!cancelled) setEvidenceError(err instanceof Error ? err.message : 'Failed to load evidence');
      })
      .finally(() => {
        if (!cancelled) setEvidenceLoading(false);
      });
    return () => { cancelled = true; };
  }, [claimId]);

  const handleViewImage = async (evidenceId: string) => {
    if (!claimId) return;
    try {
      const blob = await api.claims.downloadEvidence(claimId, evidenceId);
      const url = window.URL.createObjectURL(blob);
      setViewingFile(url);
    } catch {
      // ignore
    }
  };

  const handleDownload = async (evidenceId: string, filename: string) => {
    if (!claimId) return;
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
    } catch {
      // ignore
    }
  };

  // Resolve from agent_type: support both canonical (document) and tool (verify_document) names
  const documentResult = agentResults.find(r => r.agent_type === 'document' || r.agent_type === 'verify_document');
  const imageResult = agentResults.find(r => r.agent_type === 'image' || r.agent_type === 'verify_image');
  const fraudResult = agentResults.find(r => r.agent_type === 'fraud' || r.agent_type === 'verify_fraud');
  const crossCheckResult = agentResults.find(r => r.agent_type === 'cross_check_amounts');
  const validateResult = agentResults.find(r => r.agent_type === 'validate_claim_data');
  const estimateResult = agentResults.find(r => r.agent_type === 'estimate_repair_cost');

  const hasData = documentResult || imageResult || fraudResult || crossCheckResult || validateResult || estimateResult;

  if (!hasData) {
    return null;
  }

  return (
    <>
    <Card className="p-6 admin-card">
      <h3 className="text-sm font-medium text-slate-100 mb-4">Extracted Information Summary</h3>
      <div className="space-y-4">
        {/* Uploaded documents */}
        {claimId && (
          <div className="p-4 rounded-lg bg-slate-500/10 border border-slate-500/30">
            <h4 className="text-sm font-medium text-white mb-3">Uploaded documents</h4>
            {evidenceLoading && (
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <div className="w-3 h-3 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
                Loading…
              </div>
            )}
            {evidenceError && (
              <p className="text-xs text-amber-400">{evidenceError}</p>
            )}
            {!evidenceLoading && !evidenceError && evidence.length === 0 && (
              <p className="text-xs text-slate-400">No documents or images uploaded.</p>
            )}
            {!evidenceLoading && evidence.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {evidence.map((file) => {
                  const filename = getEvidenceFileName(file.file_path);
                  const isImage = file.file_type === 'image' || (file.mime_type != null && file.mime_type.startsWith('image/'));
                  const size = formatEvidenceFileSize(file.file_size);
                  return (
                    <div
                      key={file.id}
                      className="flex items-center gap-2 px-3 py-2 rounded-md border border-slate-600 bg-slate-800/50 text-xs"
                    >
                      {isImage ? (
                        <span className="text-purple-400" aria-hidden>🖼️</span>
                      ) : (
                        <span className="text-blue-400" aria-hidden>📄</span>
                      )}
                      <span className="text-slate-200 truncate max-w-[140px]" title={filename}>
                        {filename}
                      </span>
                      {size && <span className="text-slate-500 shrink-0">{size}</span>}
                      {isImage && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewImage(file.id)}
                          className="h-6 px-2 text-xs text-slate-300 hover:text-white"
                        >
                          View
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDownload(file.id, filename)}
                        className="h-6 px-2 text-xs text-slate-300 hover:text-white"
                      >
                        Download
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
        {/* From Documents: when extracted_data is present */}
        {documentResult?.result?.extracted_data && (() => {
          const extractedData = documentResult.result.extracted_data;
          
          // Check if extraction failed
          if (extractedData.extraction_failed || extractedData.error || 
              (extractedData.metadata?.extraction_method === 'failed') ||
              (!documentResult.result.valid && !extractedData.extracted_fields)) {
            return (
              <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-lg">📄</span>
                  <h4 className="text-sm font-medium text-white">From Documents</h4>
                </div>
                <div className="text-xs text-red-400">
                  <p className="font-medium mb-1">⚠️ Failed to Extract Document Data</p>
                  <p className="text-slate-300">
                    {extractedData.metadata?.notes || 
                     extractedData.error || 
                     documentResult.result.error ||
                     'Document extraction failed. Please ensure the API is properly configured.'}
                  </p>
                </div>
              </div>
            );
          }
          
          // Handle new structure with document_classification and extracted_fields
          const classification = extractedData.document_classification;
          const extractedFields = extractedData.extracted_fields || extractedData; // Fallback to old structure
          const lineItems = extractedData.line_items;
          const tables = extractedData.tables;
          const metadata = extractedData.metadata;
          
          // Get all fields to display (excluding nested structures)
          const fieldsToDisplay: Record<string, any> = {};
          Object.keys(extractedFields).forEach(key => {
            const value = extractedFields[key];
            // Skip nested objects and arrays (they're handled separately)
            if (value !== null && value !== undefined && 
                typeof value !== 'object' && !Array.isArray(value)) {
              fieldsToDisplay[key] = value;
            }
          });
          
          // Also include top-level fields for backward compatibility
          if (!extractedData.extracted_fields) {
            ['document_type', 'amount', 'date', 'vendor', 'description'].forEach(key => {
              if (extractedData[key] !== undefined && extractedData[key] !== null) {
                fieldsToDisplay[key] = extractedData[key];
              }
            });
          }
          
          // Don't show if no fields were extracted
          if (Object.keys(fieldsToDisplay).length === 0 && 
              (!lineItems || lineItems.length === 0) && 
              (!tables || tables.length === 0)) {
            return (
              <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-lg">📄</span>
                  <h4 className="text-sm font-medium text-white">From Documents</h4>
                </div>
                <div className="text-xs text-yellow-400">
                  <p>No data extracted from document. The document may be empty or unreadable.</p>
                </div>
              </div>
            );
          }
          
          return (
            <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/30">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-lg">📄</span>
                <h4 className="text-sm font-medium text-white">From Documents</h4>
              </div>
              
              {/* Document Classification */}
              {classification && (
                <div className="pb-3 border-b border-slate-600">
                  <div className="text-xs font-semibold text-slate-200 mb-2 uppercase tracking-wide">Document Classification</div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
                    {classification.category && classification.category !== 'unknown' && (
                      <FieldDisplay label="Category" value={classification.category} />
                    )}
                    {classification.structure && classification.structure !== 'unknown' && (
                      <FieldDisplay label="Structure" value={classification.structure} />
                    )}
                    {classification.primary_content_type && classification.primary_content_type !== 'unknown' && (
                      <FieldDisplay label="Content Type" value={classification.primary_content_type} />
                    )}
                  </div>
                </div>
              )}
              
              {/* Extracted Fields – grouped */}
              {(() => {
                const grouped = groupFields(fieldsToDisplay);
                const order = Object.keys(FIELD_GROUPS).sort(
                  (a, b) => (FIELD_GROUPS[a]?.order ?? 99) - (FIELD_GROUPS[b]?.order ?? 99)
                );
                return (
                  <div className="space-y-3 pt-4">
                    {order.map((g) => {
                      const info = FIELD_GROUPS[g];
                      const fields = grouped[g];
                      if (!fields || Object.keys(fields).length === 0) return null;
                      return (
                        <FieldGroupSection
                          key={g}
                          title={info?.label ?? g}
                          fields={fields}
                        />
                      );
                    })}
                  </div>
                );
              })()}

              {/* Line Items – tabular (currency-aware: Rs. for INR/Rs, $ for USD) */}
              {lineItems && Array.isArray(lineItems) && lineItems.length > 0 && (
                <LineItemsTable lineItems={lineItems} currency={extractedFields?.currency ?? extractedData?.currency} />
              )}

              {/* Tables (currency-aware for money columns) */}
              {tables && Array.isArray(tables) && tables.length > 0 && (
                <TablesDisplay tables={tables} currency={extractedFields?.currency ?? extractedData?.currency} />
              )}

              {/* Metadata */}
              {metadata && (
                <div className="pt-3 mt-1 border-t border-slate-600">
                  <div className="text-xs font-semibold text-slate-200 mb-2 uppercase tracking-wide">Metadata</div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
                    {metadata.confidence !== undefined && metadata.confidence > 0 && (
                      <FieldDisplay label="Confidence" value={`${(metadata.confidence * 100).toFixed(1)}%`} />
                    )}
                    {metadata.extraction_method && metadata.extraction_method !== 'failed' && (
                      <FieldDisplay label="Extraction method" value={metadata.extraction_method} />
                    )}
                  </div>
                  {metadata.notes && (
                    <div className="mt-2 text-xs">
                      <span className="text-slate-400">Notes: </span>
                      <span className="text-slate-200">{metadata.notes}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })()}

        {/* From Documents: fallback when we have a document result but no extracted_data */}
        {documentResult && !documentResult.result?.extracted_data && (
          <div className="p-4 rounded-lg bg-slate-500/10 border border-slate-500/30">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">📄</span>
              <h4 className="text-sm font-medium text-white">From Documents</h4>
            </div>
            <p className="text-xs text-slate-300">
              Document was processed. No structured extraction data is available.
              {documentResult.result?.error && (
                <span className="block mt-1 text-amber-400">Error: {String(documentResult.result.error)}</span>
              )}
            </p>
          </div>
        )}

        {/* From Images */}
        {imageResult?.result.damage_assessment && (
          <div className="p-4 rounded-lg bg-purple-500/10 border border-purple-500/30">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">🖼️</span>
              <h4 className="text-sm font-medium text-white">From Images</h4>
            </div>
            <div className="space-y-2 text-xs">
              {imageResult.result.damage_assessment.damage_type && (
                <div className="flex items-center gap-2">
                  <span className="text-slate-300">Damage Type:</span>
                  <span className="text-slate-100">
                    {imageResult.result.damage_assessment.damage_type}
                  </span>
                </div>
              )}
              {imageResult.result.damage_assessment.severity && (
                <div className="flex items-center gap-2">
                  <span className="text-slate-300">Severity:</span>
                  <span className="text-slate-100">
                    {imageResult.result.damage_assessment.severity}
                  </span>
                </div>
              )}
              {imageResult.result.damage_assessment.affected_parts && 
               Array.isArray(imageResult.result.damage_assessment.affected_parts) && (
                <div className="flex items-start gap-2">
                  <span className="text-slate-300">Affected Parts:</span>
                  <span className="text-slate-100">
                    {imageResult.result.damage_assessment.affected_parts.join(', ')}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* From Bills/Receipts */}
        {fraudResult?.result?.bill_analysis && (
          <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">🛡️</span>
              <h4 className="text-sm font-medium text-white">From Bills/Receipts</h4>
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex items-center gap-2">
                <span className="text-slate-300">Total Bill Amount:</span>
                <span className="text-slate-100 font-medium">
                  ${fraudResult.result.bill_analysis.extracted_total.toFixed(2)}
                </span>
              </div>
              {fraudResult.result.bill_analysis.recommended_amount !== undefined && 
               Math.abs(fraudResult.result.bill_analysis.recommended_amount - 
                        fraudResult.result.bill_analysis.extracted_total) > 0.01 && (
                <div className="flex items-center gap-2">
                  <span className="text-slate-300">Recommended Amount:</span>
                  <span className="text-yellow-400 font-medium">
                    ${fraudResult.result.bill_analysis.recommended_amount.toFixed(2)}
                  </span>
                </div>
              )}
              <div className="flex items-center gap-4 pt-2 border-t border-slate-700">
                <div className="flex items-center gap-1">
                  {fraudResult.result.bill_analysis.claim_amount_match ? (
                    <span className="text-green-400">✓</span>
                  ) : (
                    <span className="text-red-400">✗</span>
                  )}
                  <span className="text-slate-300">Claim Amount Match</span>
                </div>
                <div className="flex items-center gap-1">
                  {fraudResult.result.bill_analysis.document_amount_match ? (
                    <span className="text-green-400">✓</span>
                  ) : (
                    <span className="text-red-400">✗</span>
                  )}
                  <span className="text-slate-300">Document Amount Match</span>
                </div>
              </div>
              {fraudResult.result.bill_analysis.validation_summary && (
                <div className="pt-2 border-t border-slate-600">
                  <p className="text-slate-300 mb-1">Validation:</p>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="text-green-400">
                        {fraudResult.result.bill_analysis.validation_summary.valid_items_count} valid
                      </span>
                    </div>
                    <div>
                      <span className="text-red-400">
                        {fraudResult.result.bill_analysis.validation_summary.invalid_items_count} invalid
                      </span>
                    </div>
                    <div>
                      <span className="text-yellow-400">
                        {fraudResult.result.bill_analysis.validation_summary.overpriced_items_count} overpriced
                      </span>
                    </div>
                    <div>
                      <span className="text-orange-400">
                        {fraudResult.result.bill_analysis.validation_summary.irrelevant_items_count} irrelevant
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* From claim analysis: cross_check_amounts, validate_claim_data, estimate_repair_cost */}
        {(crossCheckResult || validateResult || estimateResult) && (
          <div className="p-4 rounded-lg bg-cyan-500/10 border border-cyan-500/30">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-lg">📊</span>
              <h4 className="text-sm font-medium text-white">From Claim Analysis</h4>
            </div>
            <div className="space-y-4 text-xs">
              {estimateResult?.result && typeof estimateResult.result === 'object' && (
                <div className="pb-3 border-b border-slate-600">
                  <div className="text-xs font-semibold text-slate-200 mb-2 uppercase tracking-wide">Cost estimate</div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1.5">
                    {'estimated_cost' in estimateResult.result && (
                      <FieldDisplay label="Estimated cost" value={`$${Number((estimateResult.result as Record<string, unknown>).estimated_cost).toFixed(2)}`} />
                    )}
                    {'confidence' in estimateResult.result && (
                      <FieldDisplay label="Confidence" value={`${(Number((estimateResult.result as Record<string, unknown>).confidence) * 100).toFixed(0)}%`} />
                    )}
                    {typeof (estimateResult.result as Record<string, unknown>).cost_breakdown === 'object' &&
                     (estimateResult.result as Record<string, unknown>).cost_breakdown != null ? (
                      <div className="sm:col-span-2">
                        <span className="text-slate-400">Breakdown: </span>
                        <span className="text-slate-100">
                          {JSON.stringify((estimateResult.result as Record<string, unknown>).cost_breakdown)}
                        </span>
                      </div>
                    ) : null}
                  </div>
                </div>
              )}
              {crossCheckResult?.result && typeof crossCheckResult.result === 'object' && (
                <div className="pb-3 border-b border-slate-600">
                  <div className="text-xs font-semibold text-slate-200 mb-2 uppercase tracking-wide">Amount cross-check</div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1.5">
                    {'matches' in crossCheckResult.result && (
                      <div className="flex items-center gap-2">
                        <span className="text-slate-400">Matches:</span>
                        {(crossCheckResult.result as Record<string, unknown>).matches ? (
                          <span className="text-green-400">✓ Yes</span>
                        ) : (
                          <span className="text-amber-400">✗ No</span>
                        )}
                      </div>
                    )}
                    {'difference_percent' in crossCheckResult.result && Number((crossCheckResult.result as Record<string, unknown>).difference_percent) > 0 && (
                      <FieldDisplay label="Difference" value={`${Number((crossCheckResult.result as Record<string, unknown>).difference_percent).toFixed(1)}%`} />
                    )}
                    {Array.isArray((crossCheckResult.result as Record<string, unknown>).warnings) && ((crossCheckResult.result as Record<string, unknown>).warnings as string[]).length > 0 && (
                      <div className="sm:col-span-2">
                        <span className="text-slate-400">Warnings: </span>
                        <ul className="mt-1 list-disc list-inside text-slate-200">
                          {((crossCheckResult.result as Record<string, unknown>).warnings as string[]).map((w, i) => (
                            <li key={i}>{w}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}
              {validateResult?.result && typeof validateResult.result === 'object' && (
                <div>
                  <div className="text-xs font-semibold text-slate-200 mb-2 uppercase tracking-wide">Validation</div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1.5">
                    {'recommendation' in validateResult.result && (
                      <FieldDisplay label="Recommendation" value={String((validateResult.result as Record<string, unknown>).recommendation)} />
                    )}
                    {'validation_score' in validateResult.result && (
                      <FieldDisplay label="Score" value={`${(Number((validateResult.result as Record<string, unknown>).validation_score) * 100).toFixed(0)}%`} />
                    )}
                    {'valid' in validateResult.result && (
                      <div className="flex items-center gap-2">
                        <span className="text-slate-400">Valid:</span>
                        {(validateResult.result as Record<string, unknown>).valid ? (
                          <span className="text-green-400">Yes</span>
                        ) : (
                          <span className="text-amber-400">No</span>
                        )}
                      </div>
                    )}
                    {Array.isArray((validateResult.result as Record<string, unknown>).issues) && ((validateResult.result as Record<string, unknown>).issues as string[]).length > 0 && (
                      <div className="sm:col-span-2">
                        <span className="text-slate-400">Issues: </span>
                        <ul className="mt-1 list-disc list-inside text-slate-200">
                          {((validateResult.result as Record<string, unknown>).issues as string[]).map((issue, i) => (
                            <li key={i}>{issue}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </Card>

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
              type="button"
              onClick={() => {
                setViewingFile(null);
                window.URL.revokeObjectURL(viewingFile);
              }}
              className="absolute top-6 right-6 text-white hover:text-gray-300 bg-black/50 rounded-full p-2 z-10"
              aria-label="Close"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            <img
              src={viewingFile}
              alt="Uploaded document"
              className="max-w-full max-h-[90vh] object-contain rounded-lg"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        </div>
      )}
    </>
  );
}
