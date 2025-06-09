import React, { useEffect, useState, useMemo } from 'react'; // Added useMemo
import { Link, useParams } from 'react-router-dom';
import { fetchSpaces, fetchPagesInSpace } from '../../services/api';
import { Space, Page } from '../../types/apiModels';
import PageTreeItem, { HierarchicalPage } from './PageTreeItem'; // Import PageTreeItem and HierarchicalPage
import styles from './AppSidebar.module.css';

// Helper function to build page hierarchy
const buildPageTree = (pages: Page[]): HierarchicalPage[] => {
  const pagesById: { [id: number]: HierarchicalPage } = {};
  pages.forEach(page => {
    pagesById[page.id] = { ...page, children: [] };
  });

  const tree: HierarchicalPage[] = [];
  pages.forEach(page => {
    if (page.parent && pagesById[page.parent]) {
      pagesById[page.parent].children.push(pagesById[page.id]);
    } else {
      tree.push(pagesById[page.id]);
    }
  });

  // Sort children by title, or other criteria if needed
  Object.values(pagesById).forEach(page => {
    page.children.sort((a, b) => a.title.localeCompare(b.title));
  });
  tree.sort((a,b) => a.title.localeCompare(b.title));

  return tree;
};


const AppSidebar: React.FC = () => {
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [flatPages, setFlatPages] = useState<Page[]>([]); // Store flat list of pages
  const [isLoadingSpaces, setIsLoadingSpaces] = useState(true);
  const [isLoadingPages, setIsLoadingPages] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { spaceKey: currentSpaceKey } = useParams<{ spaceKey: string; pageId: string }>(); // currentPageId not directly used here now

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
          setFlatPages(fetchedPages); // Store the flat list
          setError(null);
        } catch (err: any) { // Added type for err
          setError(`Failed to load pages for space ${currentSpaceKey}. Error: ${err.message}`);
          console.error(err);
        } finally {
          setIsLoadingPages(false);
        }
      };
      loadPages();
    } else {
      setFlatPages([]); // Clear pages if no space is selected
    }
  }, [currentSpaceKey]);

  // Memoize the hierarchical page structure
  const pageTree = useMemo(() => {
    if (flatPages.length > 0) {
      return buildPageTree(flatPages);
    }
    return [];
  }, [flatPages]);

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
                {!isLoadingPages && pageTree.length === 0 && <p>No pages in this space.</p>}
                {pageTree.length > 0 && (
                  <ul className={styles.pageTreeRoot}>
                    {pageTree.map((pageNode) => (
                      <PageTreeItem key={pageNode.id} page={pageNode} level={0} />
                    ))}
                  </ul>
                )}
              </>
            )}
          </li>
        ))}
      </ul>
    </aside>
  );
};

export default AppSidebar;
