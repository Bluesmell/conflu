import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { fetchSpaces, fetchPagesInSpace } from '../../services/api';
import { Space, Page } from '../../types/apiModels';
import styles from './AppSidebar.module.css'; // We'll create this CSS module

const AppSidebar: React.FC = () => {
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [pages, setPages] = useState<Page[]>([]);
  const [isLoadingSpaces, setIsLoadingSpaces] = useState(true);
  const [isLoadingPages, setIsLoadingPages] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { spaceKey: currentSpaceKey, pageId: currentPageId } = useParams<{ spaceKey: string; pageId: string }>();

  useEffect(() => {
    const loadSpaces = async () => {
      try {
        setIsLoadingSpaces(true);
        const fetchedSpaces = await fetchSpaces();
        setSpaces(fetchedSpaces);
        setError(null);
      } catch (err) {
        setError('Failed to load spaces.');
        console.error(err);
      } finally {
        setIsLoadingSpaces(false);
      }
    };
    loadSpaces();
  }, []);

  useEffect(() => {
    if (currentSpaceKey) {
      const loadPages = async () => {
        try {
          setIsLoadingPages(true);
          const fetchedPages = await fetchPagesInSpace(currentSpaceKey);
          setPages(fetchedPages);
          setError(null);
        } catch (err) {
          setError(`Failed to load pages for space ${currentSpaceKey}.`);
          console.error(err);
        } finally {
          setIsLoadingPages(false);
        }
      };
      loadPages();
    } else {
      setPages([]); // Clear pages if no space is selected
    }
  }, [currentSpaceKey]);

  if (isLoadingSpaces) {
    return <aside className={styles.appSidebar}><p>Loading spaces...</p></aside>;
  }

  if (error) {
    return <aside className={styles.appSidebar}><p style={{ color: 'red' }}>{error}</p></aside>;
  }

  return (
    <aside className={styles.appSidebar}>
      <h2>Spaces</h2>
      {spaces.length === 0 && !isLoadingSpaces ? <p>No spaces found.</p> : null}
      <ul>
        {spaces.map((space) => (
          <li key={space.key} className={space.key === currentSpaceKey ? styles.active : ''}>
            <Link to={`/spaces/${space.key}`}>{space.name}</Link>
            {space.key === currentSpaceKey && (
              <>
                <h3>Pages in {space.name}</h3>
                {isLoadingPages && <p>Loading pages...</p>}
                {!isLoadingPages && pages.length === 0 && <p>No pages in this space.</p>}
                <ul>
                  {pages.map((page) => (
                    <li key={page.id} className={String(page.id) === currentPageId ? styles.activeSubItem : ''}>
                      <Link to={`/spaces/${space.key}/pages/${page.id}`}>{page.title}</Link>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </li>
        ))}
      </ul>
    </aside>
  );
};

export default AppSidebar;
