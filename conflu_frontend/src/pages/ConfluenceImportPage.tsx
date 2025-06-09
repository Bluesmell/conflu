import React from 'react';
import ConfluenceImportForm from '../components/import/ConfluenceImportForm';
import styles from './ConfluenceImportPage.module.css'; // To be created

const ConfluenceImportPage: React.FC = () => {
  return (
    <div className={styles.importPageContainer}>
      <header className={styles.pageHeader}>
        <h1>Import from Confluence</h1>
        <p>Upload your Confluence space export ZIP file to begin the import process.</p>
      </header>
      <main className={styles.formSection}>
        <ConfluenceImportForm />
      </main>
    </div>
  );
};

export default ConfluenceImportPage;
