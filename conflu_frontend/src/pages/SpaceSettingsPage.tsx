import React from 'react';
import { useParams, Link } from 'react-router-dom';
import SpacePermissionsManager from '../components/permissions/SpacePermissionsManager';
import styles from './SpaceSettingsPage.module.css'; // To be created

const SpaceSettingsPage: React.FC = () => {
  const { spaceKey } = useParams<{ spaceKey: string }>();

  if (!spaceKey) {
    return <p className={styles.errorMessage}>Error: Space key is missing from URL.</p>;
  }

  // In a real app, you might have tabs for different settings (General, Permissions, etc.)
  // For now, we'll directly render the Permissions Manager.

  return (
    <div className={styles.spaceSettingsPage}>
      <nav className={styles.breadcrumbs}>
        <Link to="/">Home</Link> /
        <Link to={`/spaces/${spaceKey}`}>Space: {spaceKey}</Link> /
        <span>Settings</span>
      </nav>
      <h1>Space Settings for "{spaceKey}"</h1>

      {/* Future: Tab navigation could go here */}
      {/* <div className={styles.tabs}> ... </div> */}

      <div className={styles.settingsContent}>
        <SpacePermissionsManager spaceKey={spaceKey} />
      </div>
    </div>
  );
};

export default SpaceSettingsPage;
