/**
 * Project List Component
 */

import React from 'react';

const styles = {
  container: {
    padding: '16px',
    height: '100%',
    overflowY: 'auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
  },
  title: {
    fontSize: '18px',
    fontWeight: 'bold',
  },
  addButton: {
    background: '#4a9eff',
    border: 'none',
    borderRadius: '4px',
    padding: '8px 12px',
    color: 'white',
    cursor: 'pointer',
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  item: {
    padding: '12px',
    background: '#252540',
    borderRadius: '8px',
    cursor: 'pointer',
    border: '2px solid transparent',
    transition: 'all 0.2s',
  },
  itemSelected: {
    borderColor: '#4a9eff',
    background: '#2a2a50',
  },
  itemName: {
    fontWeight: 'bold',
    marginBottom: '4px',
  },
  itemMeta: {
    fontSize: '12px',
    color: '#888',
  },
  empty: {
    textAlign: 'center',
    color: '#666',
    padding: '32px',
  },
};

export default function ProjectList({ projects, selectedId, onSelect, onCreate }) {
  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.title}>Projects</span>
        <button style={styles.addButton} onClick={onCreate}>
          + New
        </button>
      </div>
      
      {projects.length === 0 ? (
        <div style={styles.empty}>No projects yet</div>
      ) : (
        <div style={styles.list}>
          {projects.map((project) => (
            <div
              key={project.id}
              style={{
                ...styles.item,
                ...(selectedId === project.id ? styles.itemSelected : {}),
              }}
              onClick={() => onSelect(project.id)}
            >
              <div style={styles.itemName}>{project.name || project.id}</div>
              <div style={styles.itemMeta}>
                {project.modified_at ? new Date(project.modified_at).toLocaleDateString() : ''}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
