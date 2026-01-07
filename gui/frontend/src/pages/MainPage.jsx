/**
 * Main Page
 * 3열 레이아웃: Projects | Editor/Console | Trace
 */

import React, { useState, useEffect, useCallback } from 'react';
import ProjectList from '../components/ProjectList';
import ProjectEditor from '../components/ProjectEditor';
import RunConsole from '../components/RunConsole';
import TraceViewer from '../components/TraceViewer';
import { projectsApi, runsApi, tracesApi } from '../api/client';

const styles = {
  container: {
    display: 'grid',
    gridTemplateColumns: '280px 1fr 400px',
    height: '100vh',
  },
  leftPanel: {
    background: '#16162a',
    borderRight: '1px solid #333',
  },
  centerPanel: {
    display: 'flex',
    flexDirection: 'column',
    background: '#1a1a2e',
  },
  rightPanel: {
    background: '#16162a',
    borderLeft: '1px solid #333',
  },
  tabs: {
    display: 'flex',
    borderBottom: '1px solid #333',
  },
  tab: {
    padding: '12px 24px',
    background: 'transparent',
    border: 'none',
    color: '#888',
    cursor: 'pointer',
    borderBottom: '2px solid transparent',
  },
  tabActive: {
    color: '#fff',
    borderBottomColor: '#4a9eff',
  },
  tabContent: {
    flex: 1,
    overflow: 'hidden',
  },
  header: {
    padding: '16px',
    borderBottom: '1px solid #333',
    fontSize: '18px',
    fontWeight: 'bold',
  },
  createModal: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0,0,0,0.8)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  modalContent: {
    background: '#252540',
    padding: '24px',
    borderRadius: '8px',
    width: '400px',
  },
  modalTitle: {
    fontSize: '18px',
    fontWeight: 'bold',
    marginBottom: '16px',
  },
  input: {
    width: '100%',
    padding: '12px',
    marginBottom: '12px',
    background: '#1a1a2e',
    border: '1px solid #333',
    borderRadius: '4px',
    color: 'white',
    fontSize: '14px',
  },
  modalButtons: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '8px',
    marginTop: '16px',
  },
  button: {
    padding: '8px 16px',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
};

export default function MainPage() {
  // State
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [yamlContent, setYamlContent] = useState('');
  const [activeTab, setActiveTab] = useState('editor');
  const [currentRunId, setCurrentRunId] = useState(null);
  const [trace, setTrace] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newProjectId, setNewProjectId] = useState('');
  const [loading, setLoading] = useState(false);

  // Load projects
  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const data = await projectsApi.list();
      setProjects(data);
    } catch (error) {
      console.error('Failed to load projects:', error);
    }
  };

  // Load project content
  const loadProject = async (projectId) => {
    try {
      const data = await projectsApi.get(projectId);
      setYamlContent(data.yaml_content);
      setSelectedProjectId(projectId);
      setCurrentRunId(null);
      setTrace(null);
    } catch (error) {
      console.error('Failed to load project:', error);
    }
  };

  // Create project
  const handleCreateProject = async () => {
    if (!newProjectId.trim()) return;
    
    try {
      await projectsApi.create({ id: newProjectId.trim() });
      await loadProjects();
      setShowCreateModal(false);
      setNewProjectId('');
      loadProject(newProjectId.trim());
    } catch (error) {
      alert('Failed to create project: ' + error.message);
    }
  };

  // Save project
  const handleSave = async (content) => {
    await projectsApi.update(selectedProjectId, content);
    setYamlContent(content);
    await loadProjects();
  };

  // Validate
  const handleValidate = async (content) => {
    return await projectsApi.validate(content);
  };

  // Run project
  const handleRun = async () => {
    if (!selectedProjectId) return;
    
    setLoading(true);
    try {
      const result = await runsApi.start(selectedProjectId);
      setCurrentRunId(result.run_id);
      setActiveTab('console');
      
      // 초기 trace 로드
      setTimeout(() => pollTrace(result.run_id), 500);
    } catch (error) {
      alert('Failed to start run: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // Poll trace
  const pollTrace = useCallback(async (runId = currentRunId) => {
    if (!selectedProjectId || !runId) return;
    
    try {
      const data = await tracesApi.get(selectedProjectId, runId);
      setTrace(data);
    } catch (error) {
      // Trace not ready yet
      console.log('Waiting for trace...');
    }
  }, [selectedProjectId, currentRunId]);

  return (
    <div style={styles.container}>
      {/* Left Panel: Projects */}
      <div style={styles.leftPanel}>
        <ProjectList
          projects={projects}
          selectedId={selectedProjectId}
          onSelect={loadProject}
          onCreate={() => setShowCreateModal(true)}
        />
      </div>

      {/* Center Panel: Editor / Console */}
      <div style={styles.centerPanel}>
        <div style={styles.tabs}>
          <button
            style={{ ...styles.tab, ...(activeTab === 'editor' ? styles.tabActive : {}) }}
            onClick={() => setActiveTab('editor')}
          >
            Project Editor
          </button>
          <button
            style={{ ...styles.tab, ...(activeTab === 'console' ? styles.tabActive : {}) }}
            onClick={() => setActiveTab('console')}
          >
            Run Console
          </button>
        </div>
        
        <div style={styles.tabContent}>
          {activeTab === 'editor' ? (
            <ProjectEditor
              projectId={selectedProjectId}
              yamlContent={yamlContent}
              onSave={handleSave}
              onValidate={handleValidate}
              onRun={handleRun}
              disabled={loading}
            />
          ) : (
            <RunConsole
              projectId={selectedProjectId}
              runId={currentRunId}
              trace={trace}
              onPoll={() => pollTrace()}
            />
          )}
        </div>
      </div>

      {/* Right Panel: Trace Viewer */}
      <div style={styles.rightPanel}>
        <div style={styles.header}>Trace Viewer</div>
        <TraceViewer trace={trace} />
      </div>

      {/* Create Project Modal */}
      {showCreateModal && (
        <div style={styles.createModal} onClick={() => setShowCreateModal(false)}>
          <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalTitle}>Create New Project</div>
            <input
              style={styles.input}
              placeholder="Project ID (e.g., my_project)"
              value={newProjectId}
              onChange={(e) => setNewProjectId(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreateProject()}
              autoFocus
            />
            <div style={styles.modalButtons}>
              <button
                style={{ ...styles.button, background: '#666', color: 'white' }}
                onClick={() => setShowCreateModal(false)}
              >
                Cancel
              </button>
              <button
                style={{ ...styles.button, background: '#4a9eff', color: 'white' }}
                onClick={handleCreateProject}
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
