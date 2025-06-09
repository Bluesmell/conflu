import React from 'react';
import { Outlet } from 'react-router-dom';
import AppHeader from './AppHeader';
import AppSidebar from './AppSidebar';
import styles from './AppLayout.module.css'; // We'll create this CSS module

const AppLayout: React.FC = () => {
  return (
    <div className={styles.appLayout}>
      <AppHeader />
      <div className={styles.mainContent}>
        <AppSidebar />
        <main className={styles.pageContent}>
          <Outlet /> {/* Child routes will render here */}
        </main>
      </div>
    </div>
  );
};

export default AppLayout;
