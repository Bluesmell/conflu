import React from 'react';
import { Link } from 'react-router-dom';
import styles from './AppHeader.module.css';
import GlobalSearchBar from '../search/GlobalSearchBar'; // Import the search bar

const AppHeader: React.FC = () => {
  return (
    <header className={styles.appHeader}>
      <div className={styles.logo}>
        <Link to="/">Conflu</Link>
      </div>
      <div className={styles.searchContainer}> {/* Added container for search bar */}
        <GlobalSearchBar />
      </div>
      <nav className={styles.navigation}>
        {/* Placeholder for user menu, etc. */}
        <span>User Menu</span>
      </nav>
    </header>
  );
};

export default AppHeader;
