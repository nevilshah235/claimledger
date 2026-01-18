'use client';

import { useState } from 'react';
import { Card } from './ui';
import { AgentResult } from '@/lib/types';

interface ExtractedInfoSummaryProps {
  agentResults: AgentResult[];
}

// Helper function to format field names (convert snake_case to Title Case)
function formatFieldName(key: string): string {
  return key
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// Helper function to format field values
function formatFieldValue(value: any): string {
  if (value === null || value === undefined) return 'N/A';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') {
    // Check if it's a monetary value (has decimal places or is large)
    if (value % 1 !== 0 || value > 100) {
      return `$${value.toFixed(2)}`;
    }
    return value.toString();
  }
  if (Array.isArray(value)) {
    return value.length > 0 ? value.join(', ') : 'None';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}

// Component to render a single field
function FieldDisplay({ label, value }: { label: string; value: any }) {
  if (value === null || value === undefined || value === '') return null;
  
  return (
    <div className="flex items-start gap-2">
      <span className="text-slate-400 min-w-[100px]">{label}:</span>
      <span className="text-slate-300 break-words">{formatFieldValue(value)}</span>
    </div>
  );
}

// Component to render line items
function LineItemsDisplay({ lineItems }: { lineItems: any[] }) {
  const [expanded, setExpanded] = useState(false);
  
  if (!lineItems || lineItems.length === 0) return null;
  
  return (
    <div className="pt-2 border-t border-slate-700">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-slate-400 hover:text-slate-300 text-xs mb-2"
      >
        <span>{expanded ? '▼' : '▶'}</span>
        <span>Line Items ({lineItems.length})</span>
      </button>
      {expanded && (
        <div className="space-y-2 ml-4">
          {lineItems.map((item, idx) => (
            <div key={idx} className="p-2 rounded bg-slate-800/50 text-xs">
              {item.item_name && <FieldDisplay label="Item" value={item.item_name} />}
              {item.description && <FieldDisplay label="Description" value={item.description} />}
              {item.quantity !== undefined && <FieldDisplay label="Quantity" value={item.quantity} />}
              {item.unit_price !== undefined && <FieldDisplay label="Unit Price" value={item.unit_price} />}
              {item.total !== undefined && <FieldDisplay label="Total" value={item.total} />}
              {item.sku && <FieldDisplay label="SKU" value={item.sku} />}
              {item.category && <FieldDisplay label="Category" value={item.category} />}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Component to render tables
function TablesDisplay({ tables }: { tables: any[] }) {
  const [expanded, setExpanded] = useState(false);
  
  if (!tables || tables.length === 0) return null;
  
  return (
    <div className="pt-2 border-t border-slate-700">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-slate-400 hover:text-slate-300 text-xs mb-2"
      >
        <span>{expanded ? '▼' : '▶'}</span>
        <span>Tables ({tables.length})</span>
      </button>
      {expanded && (
        <div className="space-y-3 ml-4">
          {tables.map((table, idx) => (
            <div key={idx} className="p-2 rounded bg-slate-800/50 text-xs">
              {table.summary && <FieldDisplay label="Summary" value={table.summary} />}
              {table.headers && Array.isArray(table.headers) && table.headers.length > 0 && (
                <div className="mt-2">
                  <div className="text-slate-400 mb-1">Headers: {table.headers.join(', ')}</div>
                  {table.rows && Array.isArray(table.rows) && table.rows.length > 0 && (
                    <div className="text-slate-300">
                      {table.rows.length} row(s)
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ExtractedInfoSummary({ agentResults }: ExtractedInfoSummaryProps) {
  // Extract data from different agent types
  const documentResult = agentResults.find(r => r.agent_type === 'document');
  const imageResult = agentResults.find(r => r.agent_type === 'image');
  const fraudResult = agentResults.find(r => r.agent_type === 'fraud');

  const hasData = documentResult || imageResult || fraudResult;

  if (!hasData) {
    return null;
  }

  return (
    <Card className="p-6">
      <h3 className="text-sm font-medium text-white mb-4">Extracted Information Summary</h3>
      <div className="space-y-4">
        {/* From Documents */}
        {documentResult?.result.extracted_data && (() => {
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
                <div className="mb-3 pb-3 border-b border-slate-700">
                  <div className="text-xs font-medium text-slate-300 mb-2">Document Classification</div>
                  <div className="space-y-1 text-xs">
                    {classification.category && classification.category !== 'unknown' && (
                      <FieldDisplay label="Category" value={classification.category} />
                    )}
                    {classification.structure && classification.structure !== 'unknown' && (
                      <FieldDisplay label="Structure" value={classification.structure} />
                    )}
                    {classification.primary_content_type && classification.primary_content_type !== 'unknown' && (
                      <FieldDisplay label="Content Type" value={classification.primary_content_type} />
                    )}
                    {classification.has_tables !== undefined && (
                      <FieldDisplay label="Has Tables" value={classification.has_tables} />
                    )}
                    {classification.has_line_items !== undefined && (
                      <FieldDisplay label="Has Line Items" value={classification.has_line_items} />
                    )}
                  </div>
                </div>
              )}
              
              {/* Extracted Fields */}
              <div className="space-y-2 text-xs">
                {Object.entries(fieldsToDisplay).map(([key, value]) => (
                  <FieldDisplay key={key} label={formatFieldName(key)} value={value} />
                ))}
              </div>
              
              {/* Line Items */}
              {lineItems && Array.isArray(lineItems) && lineItems.length > 0 && (
                <LineItemsDisplay lineItems={lineItems} />
              )}
              
              {/* Tables */}
              {tables && Array.isArray(tables) && tables.length > 0 && (
                <TablesDisplay tables={tables} />
              )}
              
              {/* Metadata */}
              {metadata && (
                <div className="pt-2 mt-2 border-t border-slate-700 text-xs">
                  <div className="text-slate-400 mb-1">Metadata</div>
                  {metadata.confidence !== undefined && metadata.confidence > 0 && (
                    <FieldDisplay label="Confidence" value={`${(metadata.confidence * 100).toFixed(1)}%`} />
                  )}
                  {metadata.extraction_method && metadata.extraction_method !== 'failed' && (
                    <FieldDisplay label="Extraction Method" value={metadata.extraction_method} />
                  )}
                  {metadata.notes && (
                    <div className="mt-1">
                      <span className="text-slate-400">Notes: </span>
                      <span className="text-slate-300">{metadata.notes}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })()}

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
                  <span className="text-slate-400">Damage Type:</span>
                  <span className="text-slate-300">
                    {imageResult.result.damage_assessment.damage_type}
                  </span>
                </div>
              )}
              {imageResult.result.damage_assessment.severity && (
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">Severity:</span>
                  <span className="text-slate-300">
                    {imageResult.result.damage_assessment.severity}
                  </span>
                </div>
              )}
              {imageResult.result.damage_assessment.affected_parts && 
               Array.isArray(imageResult.result.damage_assessment.affected_parts) && (
                <div className="flex items-start gap-2">
                  <span className="text-slate-400">Affected Parts:</span>
                  <span className="text-slate-300">
                    {imageResult.result.damage_assessment.affected_parts.join(', ')}
                  </span>
                </div>
              )}
              {imageResult.result.damage_assessment.estimated_cost !== undefined && (
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">Estimated Cost:</span>
                  <span className="text-purple-400 font-medium">
                    ${Number(imageResult.result.damage_assessment.estimated_cost).toFixed(2)}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* From Bills/Receipts */}
        {fraudResult?.result.bill_analysis && (
          <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">🛡️</span>
              <h4 className="text-sm font-medium text-white">From Bills/Receipts</h4>
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex items-center gap-2">
                <span className="text-slate-400">Total Bill Amount:</span>
                <span className="text-slate-300 font-medium">
                  ${fraudResult.result.bill_analysis.extracted_total.toFixed(2)}
                </span>
              </div>
              {fraudResult.result.bill_analysis.recommended_amount !== undefined && 
               Math.abs(fraudResult.result.bill_analysis.recommended_amount - 
                        fraudResult.result.bill_analysis.extracted_total) > 0.01 && (
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">Recommended Amount:</span>
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
                  <span className="text-slate-400">Claim Amount Match</span>
                </div>
                <div className="flex items-center gap-1">
                  {fraudResult.result.bill_analysis.document_amount_match ? (
                    <span className="text-green-400">✓</span>
                  ) : (
                    <span className="text-red-400">✗</span>
                  )}
                  <span className="text-slate-400">Document Amount Match</span>
                </div>
              </div>
              {fraudResult.result.bill_analysis.validation_summary && (
                <div className="pt-2 border-t border-slate-700">
                  <p className="text-slate-400 mb-1">Validation:</p>
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
      </div>
    </Card>
  );
}
