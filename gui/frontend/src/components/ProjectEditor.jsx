/**
 * Project Editor Component
 * Monaco YAML Editor
 */

import React, { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
  },
  toolbar: {
    display: 'flex',
    gap: '8px',
    padding: '12px',
    background: '#1e1e30',
    borderBottom: '1px solid #333',
  },
  button: {
    padding: '8px 16px',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontWeight: 'bold',
  },
  validateBtn: {
    background: '#666',
    color: 'white',
  },
  saveBtn: {
    background: '#4a9eff',
    color: 'white',
  },
  runBtn: {
    background: '#4CAF50',
    color: 'white',
  },
  status: {
    marginLeft: 'auto',
    padding: '8px',
    fontSize: '14px',
  },
  statusSuccess: {
    color: '#4CAF50',
  },
  statusError: {
    color: '#f44336',
  },
  editor: {
    flex: 1,
  },
  placeholder: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: '#666',
    fontSize: '18px',
  },
};

export default function ProjectEditor({ 
  projectId, 
  yamlContent, 
  onSave, 
  onValidate, 
  onRun,
  disabled 
}) {
  const [content, setContent] = useState(yamlContent || '');
  const [status, setStatus] = useState({ message: '', type: '' });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setContent(yamlContent || '');
  }, [yamlContent]);

  const handleValidate = async () => {
    try {
      const result = await onValidate(content);
      if (result.valid) {
        setStatus({ message: '✓ Valid YAML', type: 'success' });
      } else {
        setStatus({ message: `✗ ${result.errors.join(', ')}`, type: 'error' });
      }
    } catch (error) {
      setStatus({ message: `✗ ${error.message}`, type: 'error' });
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(content);
      setStatus({ message: '✓ Saved', type: 'success' });
    } catch (error) {
      setStatus({ message: `✗ ${error.message}`, type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleRun = async () => {
    try {
      await onRun();
      setStatus({ message: '▶ Run started', type: 'success' });
    } catch (error) {
      setStatus({ message: `✗ ${error.message}`, type: 'error' });
    }
  };

  if (!projectId) {
    return (
      <div style={styles.placeholder}>
        Select a project to edit
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.toolbar}>
        <button 
          style={{ ...styles.button, ...styles.validateBtn }}
          onClick={handleValidate}
          disabled={disabled}
        >
          Validate
        </button>
        <button 
          style={{ ...styles.button, ...styles.saveBtn }}
          onClick={handleSave}
          disabled={disabled || saving}
        >
          {saving ? 'Saving...' : 'Save'}
        </button>
        <button 
          style={{ ...styles.button, ...styles.runBtn }}
          onClick={handleRun}
          disabled={disabled}
        >
          ▶ Run
        </button>
        
        {status.message && (
          <span style={{
            ...styles.status,
            ...(status.type === 'success' ? styles.statusSuccess : styles.statusError)
          }}>
            {status.message}
          </span>
        )}
      </div>
      
      <div style={styles.editor}>
        <Editor
          height="100%"
          defaultLanguage="yaml"
          theme="vs-dark"
          value={content}
          onChange={(value) => setContent(value || '')}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            tabSize: 2,
            wordWrap: 'on',
          }}
        />
      </div>
    </div>
  );
}
