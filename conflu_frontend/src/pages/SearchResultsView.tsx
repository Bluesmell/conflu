import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { searchPages } from '../services/api'; // Will add this to api.ts
import { PageSearchSerializer as PageSearchResult } from '../types/apiModels'; // Assuming PageSearchSerializer type is in apiModels
                                                                            // Or create a dedicated type if PageSearchSerializer is just backend
import styles from './SearchResultsView.module.css'; // CSS module for styling

// If PageSearchSerializer is not directly usable as a type, define one:
interface PageSearchItem {
  id: number;
  title: string;
  slug: string;
  space_key: string | null;
  space_name: string | null;
  updated_at: string;
  headline: string;
  rank: number;
}


const SearchResultsView: React.FC = () => {
  const [searchParams] = useSearchParams();
  const query = searchParams.get('q');
  const [results, setResults] = useState<PageSearchItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // TODO: Add pagination state: currentPage, totalPages, etc.

  useEffect(() => {
    if (query) {
      const fetchResults = async () => {
        setIsLoading(true);
        setError(null);
        try {
          // Assuming searchPages returns an array of PageSearchResult like items
          // It might be nested under a 'results' key or have pagination info
          const apiResponse = await searchPages(query);
          // For now, assume apiResponse is directly the array of results
          // Adjust if backend returns { count, next, previous, results: [] }
          setResults(apiResponse as unknown as PageSearchItem[]); // Cast if PageSearchSerializer type not directly usable
        } catch (err: any) {
          console.error('Failed to fetch search results:', err);
          setError(err.message || 'Failed to fetch search results.');
        } finally {
          setIsLoading(false);
        }
      };
      fetchResults();
    } else {
      setResults([]); // Clear results if no query
    }
  }, [query]);

  if (isLoading) {
    return <p className={styles.loadingMessage}>Searching for "{query}"...</p>;
  }

  if (error) {
    return <p className={styles.errorMessage}>Error: {error}</p>;
  }

  if (!query) {
    return <p className={styles.infoMessage}>Please enter a search term.</p>;
  }

  return (
    <div className={styles.searchResultsPage}>
      <h1>Search Results for "{query}"</h1>
      {results.length === 0 ? (
        <p className={styles.noResultsMessage}>No results found for "{query}".</p>
      ) : (
        <ul className={styles.resultsList}>
          {results.map((page) => (
            <li key={page.id} className={styles.resultItem}>
              <h2>
                <Link to={`/spaces/${page.space_key}/pages/${page.id}`}>{page.title}</Link> {/* Adjust link if slug is preferred/available */}
              </h2>
              {page.headline && (
                <p
                  className={styles.headline}
                  dangerouslySetInnerHTML={{ __html: page.headline }} // Assuming headline contains <mark> tags
                />
              )}
              <div className={styles.metaInfo}>
                <span>Space: {page.space_name || page.space_key || 'N/A'}</span>
                <span>Last Updated: {new Date(page.updated_at).toLocaleDateString()}</span>
                <span>Rank: {page.rank.toFixed(2)}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
      {/* TODO: Add pagination controls here */}
    </div>
  );
};

export default SearchResultsView;
