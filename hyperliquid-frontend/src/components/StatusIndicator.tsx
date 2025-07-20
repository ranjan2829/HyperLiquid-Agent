'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import { StatusResponse } from '@/types/api';
import { CheckCircle, XCircle, AlertCircle, Loader2 } from 'lucide-react';

export default function StatusIndicator() {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const statusData = await apiClient.getStatus();
      setStatus(statusData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center space-x-2 text-gray-400">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm">Checking status...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center space-x-2 text-red-600">
        <XCircle className="h-4 w-4" />
        <span className="text-sm">API Offline</span>
      </div>
    );
  }

  if (!status) return null;

  const getStatusIcon = () => {
    if (status.agent_ready && status.vector_store_connected) {
      return <CheckCircle className="h-4 w-4 text-green-600" />;
    } else if (status.agent_ready) {
      return <AlertCircle className="h-4 w-4 text-yellow-600" />;
    } else {
      return <XCircle className="h-4 w-4 text-red-600" />;
    }
  };

  const getStatusText = () => {
    if (status.agent_ready && status.vector_store_connected) {
      return 'All Systems Operational';
    } else if (status.agent_ready) {
      return 'Agent Ready, Vector Store Issues';
    } else {
      return 'System Degraded';
    }
  };

  return (
    <div className="flex items-center space-x-2">
      {getStatusIcon()}
      <span className="text-sm font-medium">{getStatusText()}</span>
      {status.total_documents !== null && (
        <span className="text-xs text-gray-500">
          ({status.total_documents} docs)
        </span>
      )}
    </div>
  );
}