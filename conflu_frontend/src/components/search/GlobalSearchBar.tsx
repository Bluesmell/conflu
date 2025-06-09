import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './GlobalSearchBar.module.css'; // CSS module for styling

const GlobalSearchBar: React.FC = () => {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  const handleSearchSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query.trim())}`);
      setQuery(''); // Optionally clear query from bar after search
    }
  };

  return (
    <form onSubmit={handleSearchSubmit} className={styles.searchBarForm}>
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search pages..."
        className={styles.searchInput}
        aria-label="Search pages"
      />
      <button type="submit" className={styles.searchButton}>
        Search
      </button>
    </form>
  );
};

export default GlobalSearchBar;
